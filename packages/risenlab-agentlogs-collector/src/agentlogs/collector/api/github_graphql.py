import base64
from typing import Any

from .errors import NotFoundError
from .graphql import GraphQLAPI
from .responses import AutoMerge, Label, PullRequest, PullRequestBranch, RepositoryRef, User, UserRef
from .tokens import TokenStore

PULL_REQUEST_SELECTION = """
databaseId
id
number
title
body
state
isDraft
locked
activeLockReason
createdAt
updatedAt
closedAt
mergedAt
merged
mergeable
mergeStateStatus
additions
deletions
changedFiles
authorAssociation
maintainerCanModify
author {
    __typename
    login
    ... on User { id databaseId }
    ... on Bot { id databaseId }
    ... on Organization { id databaseId }
    ... on Mannequin { id }
    ... on EnterpriseUserAccount { id login }
}
assignees(first: 20) {
    nodes {
        __typename
        id
        databaseId
        login
    }
}
reviewRequests(first: 20) {
    nodes {
        requestedReviewer {
            __typename
            ... on User { id databaseId login }
            ... on Bot { id databaseId login }
        }
    }
}
mergedBy {
    __typename
    login
    ... on User { id databaseId }
    ... on Bot { id databaseId }
    ... on Organization { id databaseId }
    ... on Mannequin { id }
    ... on EnterpriseUserAccount { id login }
}
labels(first: 20) {
    nodes { name }
}
autoMergeRequest {
    mergeMethod
    commitHeadline
    commitBody
    enabledBy {
        __typename
        login
        ... on User { id databaseId }
        ... on Bot { id databaseId }
        ... on Organization { id databaseId }
        ... on Mannequin { id }
        ... on EnterpriseUserAccount { id login }
    }
}
headRefName
headRefOid
headRepository {
    databaseId
    id
    nameWithOwner
}
baseRefName
baseRefOid
repository {
    databaseId
    id
    nameWithOwner
}
"""


class GitHubGraphQLAPI(GraphQLAPI):
    def __init__(self, token_store: TokenStore):
        super().__init__(
            token_store,
            "https://api.github.com/graphql",
            headers={
                "Accept": "application/json",
            },
        )

    async def request_pr_from_global_id(self, graphql_id: str) -> PullRequest:
        query = f"""
        query($id: ID!) {{
            node(id: $id) {{
                ... on PullRequest {{
                    {PULL_REQUEST_SELECTION}
                }}
            }}
        }}
        """
        response = await self.request(query, {"id": graphql_id}, estimated_cost=1)
        return pull_request_from_graphql(response["data"]["node"])

    async def request_pr_from_number(self, repository: str, number: int) -> PullRequest:
        owner, name = repository.split("/", 1)
        query = f"""
        query($owner: String!, $name: String!, $number: Int!) {{
            repository(owner: $owner, name: $name) {{
                pullRequest(number: $number) {{
                    {PULL_REQUEST_SELECTION}
                }}
            }}
        }}
        """
        response = await self.request(
            query,
            {"owner": owner, "name": name, "number": number},
            estimated_cost=1,
        )
        repository_node = response["data"]["repository"]
        if repository_node is None:
            raise NotFoundError("Resource not found")
        return pull_request_from_graphql(repository_node["pullRequest"])

    async def request_pr_from_minted_id(self, rest_id: int) -> PullRequest:
        return await self.request_pr_from_global_id(
            base64.b64encode(f"011:PullRequest{rest_id}".encode()).decode()
        )

    async def request_user_from_login(self, login: str) -> User:
        query = """
        query($login: String!) {
            repositoryOwner(login: $login) {
                __typename
                id
                login
                ... on User { databaseId createdAt }
                ... on Organization { databaseId createdAt }
            }
        }
        """
        response = await self.request(query, {"login": login}, estimated_cost=1)
        return user_from_graphql_node(response["data"]["repositoryOwner"])

    async def request_user_from_node_id(self, node_id: str) -> User:
        query = """
        query($id: ID!) {
            node(id: $id) {
                __typename
                id
                ... on User { databaseId login createdAt }
                ... on Organization { databaseId login createdAt }
                ... on Bot { databaseId login createdAt }
                ... on Mannequin { login }
                ... on EnterpriseUserAccount { login }
            }
        }
        """
        response = await self.request(query, {"id": node_id}, estimated_cost=1)
        return user_from_graphql_node(response["data"]["node"])

    async def request_user_from_minted_id(self, user_id: int) -> User:
        return await self.request_user_from_node_id(
            base64.b64encode(f"04:User{user_id}".encode()).decode()
        )


def user_from_graphql_node(node: dict[str, Any] | None) -> User:
    if node is None or node.get("__typename") is None or node.get("id") is None:
        raise NotFoundError("Resource not found")
    typename = node["__typename"]
    if typename in {"Mannequin", "EnterpriseUserAccount"}:
        if not node.get("login"):
            raise NotFoundError("Resource not found")
        return User(
            login=node["login"],
            type=typename,
            node_id=node["id"],
        )
    if node.get("databaseId") is None or node.get("login") is None:
        raise NotFoundError("Resource not found")
    body = User(
        id=node["databaseId"],
        login=node["login"],
        type=typename,
        node_id=node["id"],
    )
    if node.get("createdAt") is not None:
        body["created_at"] = node["createdAt"]
    return body


def graphql_user(node: dict[str, Any] | None) -> UserRef | None:
    if node is None:
        return None
    user = UserRef()
    if node.get("databaseId") is not None:
        user["id"] = node["databaseId"]
    if node.get("login") is not None:
        user["login"] = node["login"]
    if node.get("id") is not None:
        user["node_id"] = node["id"]
    if node.get("__typename") is not None:
        user["type"] = node["__typename"]
    if not user.get("id") and not user.get("login"):
        return None
    return user


def pull_request_from_graphql(node: dict[str, Any] | None) -> PullRequest:
    if node is None or "number" not in node:
        raise NotFoundError("Resource not found")

    state = str(node["state"]).lower()
    merged = node["merged"]
    if state == "merged":
        state = "closed"
        merged = True

    assignees: list[UserRef] = []
    for item in node["assignees"]["nodes"]:
        user = graphql_user(item)
        if user is not None:
            assignees.append(user)

    reviewers: list[UserRef] = []
    if node.get("reviewRequests") is not None:
        for item in node["reviewRequests"]["nodes"]:
            reviewer = item["requestedReviewer"]
            if reviewer is None or reviewer["__typename"] in {"Team", "EnterpriseTeam"}:
                continue
            user = graphql_user(reviewer)
            if user is not None:
                reviewers.append(user)

    labels: list[Label] = []
    if node.get("labels") is not None:
        labels = [Label(name=item["name"]) for item in node["labels"]["nodes"]]

    auto_merge = None
    auto_merge_request = node.get("autoMergeRequest")
    if auto_merge_request is not None:
        auto_merge = AutoMerge(
            merge_method=str(auto_merge_request["mergeMethod"]).lower(),
            commit_title=auto_merge_request.get("commitHeadline"),
            commit_message=auto_merge_request.get("commitBody"),
            enabled_by=graphql_user(auto_merge_request.get("enabledBy")),
        )

    repository = node["repository"]
    lock_reason = {
        "OFF_TOPIC": "off-topic",
        "TOO_HEATED": "too heated",
        "RESOLVED": "resolved",
        "SPAM": "spam",
        None: None,
    }[node.get("activeLockReason")]
    payload = PullRequest(
        id=node.get("databaseId"),
        node_id=node["id"],
        number=node["number"],
        title=node["title"],
        body=node["body"] or None,
        state=state,
        locked=node["locked"],
        draft=node["isDraft"],
        user=graphql_user(node.get("author")),
        labels=labels,
        active_lock_reason=lock_reason,
        created_at=node["createdAt"],
        updated_at=node["updatedAt"],
        closed_at=node.get("closedAt"),
        merged_at=node.get("mergedAt"),
        merged=merged,
        assignees=assignees,
        requested_reviewers=reviewers,
        head=pull_request_branch(
            node["headRefName"],
            node["headRefOid"],
            node["headRepository"],
        ),
        base=pull_request_branch(
            node["baseRefName"],
            node["baseRefOid"],
            repository,
        ),
        author_association=node["authorAssociation"],
        auto_merge=auto_merge,
        merged_by=graphql_user(node.get("mergedBy")),
        maintainer_can_modify=node["maintainerCanModify"],
        additions=node["additions"],
        deletions=node["deletions"],
        changed_files=node["changedFiles"],
    )
    payload["mergeable"] = {
        "MERGEABLE": True,
        "CONFLICTING": False,
        "UNKNOWN": None,
    }[node["mergeable"]]
    payload["mergeable_state"] = str(node["mergeStateStatus"]).lower()
    return payload


def pull_request_branch(
    ref: str,
    sha: str,
    repository_node: dict[str, Any] | None,
) -> PullRequestBranch:
    if repository_node is None:
        return PullRequestBranch(ref=ref, sha=sha, repo=None)
    repo = RepositoryRef(full_name=repository_node["nameWithOwner"])
    if repository_node.get("databaseId") is not None:
        repo["id"] = repository_node["databaseId"]
    return PullRequestBranch(ref=ref, sha=sha, repo=repo)

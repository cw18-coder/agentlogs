from typing import Any

from ..api.responses import PullRequest
from ..priorities import PRIORITIES
from ..runtime.resolver import ResolveJob, Resolver, Step
from ..resources import PullRequestDraft, PullRequestTimelineDraft, UserDraft
from ..runtime.processor import Result
from .collect_pull_request_timeline import CollectPullRequestTimelineJobDraft
from .collect_user import ResolveUser, user_reference_draft


class ResolvePullRequest(Resolver):
    resource_type = "pull_request"
    graphql = (
        Step(
            resolve_using="graphql_global_id",
            required_aliases=("graphql_id",),
            priority=PRIORITIES["collect_pull_request_graphql_global_id"],
            fetch=lambda api, aliases: api.request_pr_from_global_id(aliases["graphql_id"]),
        ),
        Step(
            resolve_using="graphql_number_repo",
            required_aliases=("repository_name", "number"),
            priority=PRIORITIES["collect_pull_request_graphql_number_repo"],
            fetch=lambda api, aliases: api.request_pr_from_number(
                aliases["repository_name"],
                int(aliases["number"]),
            ),
        ),
        Step(
            resolve_using="graphql_mint_global_id",
            required_aliases=("id",),
            priority=PRIORITIES["collect_pull_request_graphql_mint_global_id"],
            fetch=lambda api, aliases: api.request_pr_from_minted_id(int(aliases["id"])),
        ),
    )
    rest = (
        Step(
            resolve_using="rest_number_repo",
            required_aliases=("repository_name", "number"),
            priority=PRIORITIES["collect_pull_request_rest_number_repo"],
            fetch=lambda api, aliases: api.request_pr(
                aliases["repository_name"],
                int(aliases["number"]),
            ),
        ),
    )

    @classmethod
    def resolved(cls, body: dict[str, Any], job: ResolveJob) -> Result:
        payload: PullRequest = body
        repository_name = payload["base"]["repo"]["full_name"].lower()
        number = payload["number"]
        timeline = PullRequestTimelineDraft(
            repository_name=repository_name,
            number=number,
        )
        pull_request = PullRequestDraft(
            id=payload["id"],
            graphql_id=payload["node_id"],
            number=number,
            repository_name=repository_name,
            payload=payload,
            relations_to={"pull_request_timeline": [timeline]},
            metadata={"found_using": job.resolve_using},
        )
        references: list[tuple[str, object]] = []
        if payload.get("user") is not None:
            references.append(("pull_requests", payload.get("user")))
        for user in payload.get("assignees") or []:
            references.append(("assigned_pull_requests", user))
        for user in payload.get("requested_reviewers") or []:
            references.append(("review_requested_pull_requests", user))
        if payload.get("merged_by") is not None:
            references.append(("merged_pull_requests", payload.get("merged_by")))
        auto_merge = payload.get("auto_merge")
        if isinstance(auto_merge, dict) and auto_merge.get("enabled_by") is not None:
            references.append(("auto_merge_enabled_pull_requests", auto_merge.get("enabled_by")))
        user_drafts: list[UserDraft] = []
        for relation_type, reference in references:
            user_drafts.append(user_reference_draft(
                reference,
                relations_to={relation_type: [pull_request]},
            ))
        return Result(
            resources=[
                pull_request,
                timeline,
                *user_drafts,
            ],
            jobs=[
                CollectPullRequestTimelineJobDraft(
                    repository_name=repository_name,
                    number=int(number),
                    resource=timeline,
                ),
                *ResolveUser.next_jobs(user_drafts),
            ],
            cancel_jobs=list(ResolveUser.obsolete_jobs(user_drafts)),
        )

    @classmethod
    def unfound(cls, job: ResolveJob) -> Result:
        return Result(
            resources=[
                PullRequestDraft(
                    id=job.aliases.get("id"),
                    graphql_id=job.aliases.get("graphql_id"),
                    repository_name=job.aliases.get("repository_name"),
                    number=job.aliases.get("number"),
                    found=False,
                )
            ]
        )

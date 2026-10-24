from typing import ClassVar

from agentlogs.schema import PullRequest, UserReference
from agentlogs.schema.types.pull_request import PullRequestAutoMergeData
from agentlogs.schema.types.references import BranchCommitReference
from ..api.responses import (
    AutoMerge,
    PullRequestBranch,
)
from ..datetime import parse_utc_datetime
from .exporter import Exporter
from .common import (
    format_optional_datetime,
    format_repository_reference,
    format_session_reference,
    format_task_reference,
    format_user_reference,
)
from ..state import ResourceRecord


class PullRequestExporter(Exporter[PullRequest]):
    resource_type: ClassVar[str] = "pull_request"
    expand_relations: ClassVar[list[str]] = [
        "repository_pull_request",
        "task_pull_request",
        "session_pull_request",
        "pull_request_timeline",
        "pull_requests",
        "assigned_pull_requests",
        "review_requested_pull_requests",
        "merged_pull_requests",
        "auto_merge_enabled_pull_requests",
    ]

    def get_record_type(self) -> type[PullRequest]:
        return PullRequest

    def format_branch_data(self, payload: PullRequestBranch) -> BranchCommitReference:
        return BranchCommitReference(
            ref=payload["ref"],
            sha=payload["sha"],
        )

    def format_auto_merge_data(
        self,
        payload: AutoMerge | None,
        enabled_by: UserReference | None,
    ) -> PullRequestAutoMergeData | None:
        if payload is None:
            return None
        return PullRequestAutoMergeData(
            enabled_by=enabled_by,
            merge_method=payload.get("merge_method"),
            commit_title=payload.get("commit_title"),
            commit_message=payload.get("commit_message"),
        )

    def format_resource(
        self,
        resource: ResourceRecord,
        expanded_resources_from: dict[str, list[ResourceRecord]],
        expanded_resources_to: dict[str, list[ResourceRecord]]
    ) -> PullRequest | None:
        if resource.found is not True:
            return None
        if not isinstance(resource.payload, dict):
            raise ValueError("Pull request payload must be a dict when found")

        repositories = expanded_resources_to.get("repository_pull_request", [])
        if len(repositories) != 1:
            raise ValueError("Pull request must have exactly one repository")

        found_using = resource.metadata.get("found_using")
        if not found_using:
            raise ValueError("Pull request is missing found_using")
        if "graphql_id" not in resource.aliases:
            raise ValueError("Pull request is missing graphql_id alias")
        if "repository_name:number" not in resource.aliases:
            raise ValueError("Pull request is missing number alias")

        timelines = expanded_resources_to.get("pull_request_timeline", [])
        if len(timelines) != 1:
            raise ValueError("Pull request must have exactly one timeline")
        timeline_found = timelines[0].found is True

        pull_request_users = expanded_resources_from.get("pull_requests", [])
        if len(pull_request_users) > 1:
            raise ValueError("Pull request has more than one user")
        merged_by = expanded_resources_from.get("merged_pull_requests", [])
        if len(merged_by) > 1:
            raise ValueError("Pull request has more than one merged_by user")
        enabled_by = expanded_resources_from.get("auto_merge_enabled_pull_requests", [])
        if len(enabled_by) > 1:
            raise ValueError("Pull request has more than one auto_merge.enabled_by user")

        return PullRequest(
            id=int(resource.aliases["id"]) if "id" in resource.aliases else None,
            graphql_id=resource.aliases["graphql_id"],
            number=int(resource.aliases["repository_name:number"].rsplit(":", 1)[-1]),
            found_using=found_using,
            timeline_found=timeline_found,
            repository=format_repository_reference(repositories[0]),
            user=format_user_reference(pull_request_users[0]) if pull_request_users else None,
            assignees=[
                format_user_reference(related)
                for related in expanded_resources_from.get("assigned_pull_requests", [])
            ],
            requested_reviewers=[
                format_user_reference(related)
                for related in expanded_resources_from.get("review_requested_pull_requests", [])
            ],
            merged_by=format_user_reference(merged_by[0]) if merged_by else None,
            created_by_tasks=[
                format_task_reference(related)
                for related in expanded_resources_to.get("task_pull_request", [])
                if related.metadata.get("unattached") != "true"
            ],
            created_by_sessions=[
                format_session_reference(related)
                for related in expanded_resources_to.get("session_pull_request", [])
                if related.metadata.get("unattached") != "true"
            ],
            title=resource.payload["title"],
            body=resource.payload.get("body"),
            state=resource.payload["state"],
            locked=resource.payload["locked"],
            draft=resource.payload["draft"],
            labels=[
                name
                for item in resource.payload["labels"]
                if (name := item.get("name"))
            ],
            active_lock_reason=resource.payload.get("active_lock_reason"),
            created_at=parse_utc_datetime(resource.payload["created_at"]),
            updated_at=parse_utc_datetime(resource.payload["updated_at"]),
            closed_at=format_optional_datetime(resource.payload.get("closed_at")),
            merged_at=format_optional_datetime(resource.payload.get("merged_at")),
            head=self.format_branch_data(resource.payload["head"]),
            base=self.format_branch_data(resource.payload["base"]),
            author_association=resource.payload["author_association"],
            auto_merge=self.format_auto_merge_data(
                resource.payload.get("auto_merge"),
                format_user_reference(enabled_by[0]) if enabled_by else None,
            ),
            merged=resource.payload["merged"],
            mergeable=resource.payload.get("mergeable"),
            mergeable_state=resource.payload["mergeable_state"],
            maintainer_can_modify=resource.payload["maintainer_can_modify"],
            additions_count=resource.payload["additions"],
            deletions_count=resource.payload["deletions"],
            changed_files_count=resource.payload["changed_files"],
        )

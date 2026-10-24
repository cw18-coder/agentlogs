from typing import ClassVar

from agentlogs.schema import PullRequestTimelineEvent
from .exporter import Exporter
from .common import (
    format_optional_datetime,
    format_pull_request_reference,
    format_user_reference,
)
from ..state import ResourceRecord


class PullRequestTimelineExporter(Exporter[PullRequestTimelineEvent]):
    resource_type: ClassVar[str] = "pull_request_timeline_event"
    expand_relations: ClassVar[list[str]] = [
        "pull_request_timeline_event",
        "timeline_events",
        "assigned_timeline_events",
    ]
    load_relations_for: ClassVar[list[str]] = ["pull_request"]

    def get_record_type(self) -> type[PullRequestTimelineEvent]:
        return PullRequestTimelineEvent

    def format_resource(
        self,
        resource: ResourceRecord,
        expanded_resources_from: dict[str, list[ResourceRecord]],
        expanded_resources_to: dict[str, list[ResourceRecord]],
    ) -> PullRequestTimelineEvent | None:
        if resource.found is not True:
            return None
        pull_requests = expanded_resources_to.get("pull_request_timeline_event", [])
        if len(pull_requests) != 1:
            raise ValueError("Timeline event must have exactly one pull request")
        payload = resource.payload
        if not isinstance(payload, dict):
            raise ValueError("timeline event payload must be an object")
        alias = resource.aliases.get("repository_name:number:index")
        if alias is None:
            raise ValueError("Timeline event is missing repository_name:number:index")
        label = payload.get("label")
        if isinstance(label, dict):
            label_name = label.get("name")
        elif isinstance(label, str):
            label_name = label
        else:
            label_name = None
        created_at = payload.get("created_at")
        if created_at in (None, ""):
            created_at = payload.get("submitted_at")
        if created_at in (None, ""):
            author = payload.get("author")
            if isinstance(author, dict):
                created_at = author.get("date")
        actor = payload.get("actor")
        if actor is None:
            actor = payload.get("user")
        actors = expanded_resources_from.get("timeline_events", [])
        if actor is None:
            if actors:
                raise ValueError("timeline event has a timeline_events relation without a user")
            actor_reference = None
        elif len(actors) != 1:
            raise ValueError(f"timeline event timeline_events matched {len(actors)} users")
        else:
            actor_reference = format_user_reference(actors[0])
        assignee = payload.get("assignee")
        assignees = expanded_resources_from.get("assigned_timeline_events", [])
        if assignee is None:
            if assignees:
                raise ValueError("timeline event has an assigned_timeline_events relation without a user")
            assignee_reference = None
        elif len(assignees) != 1:
            raise ValueError(f"timeline event assigned_timeline_events matched {len(assignees)} users")
        else:
            assignee_reference = format_user_reference(assignees[0])
        commit_id = payload.get("commit_id")
        if commit_id in (None, ""):
            commit_id = payload.get("sha")
        return PullRequestTimelineEvent(
            pull_request=format_pull_request_reference(pull_requests[0]),
            event_index=int(alias.rsplit(":", 1)[-1]),
            event=payload["event"],
            created_at=format_optional_datetime(created_at),
            actor=actor_reference,
            assignee=assignee_reference,
            label=label_name,
            commit_id=commit_id,
            message=payload.get("message"),
        )

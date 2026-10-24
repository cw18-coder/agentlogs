from typing import ClassVar, cast

from agentlogs.schema import User
from agentlogs.schema.types.pull_request import PullRequestTimelineReference
from ..api.responses import User as UserPayload
from ..resources import PullRequestRef
from .exporter import Exporter
from .common import (
    format_pull_request_reference,
    format_repository_reference,
    format_session_reference,
    format_task_reference,
    format_workflow_run_reference,
)
from ..state import ResourceRecord
from ..datetime import parse_utc_datetime


class UserExporter(Exporter[User]):
    resource_type: ClassVar[str] = "user"
    expand_relations: ClassVar[list[str]] = [
        "session_user",
        "task_creator",
        "repository_owner",
    ]
    load_relations_for: ClassVar[list[str]] = []

    def get_record_type(self) -> type[User]:
        return User

    def prepare_page(self, resources: list[ResourceRecord]) -> None:
        numbers: set[str] = set()
        for resource in resources:
            for relation_type in ("timeline_events", "assigned_timeline_events"):
                for ref in resource.relations_to.get(relation_type, []):
                    if ref.alias.key != "repository_name:number:index":
                        raise ValueError("Timeline event is missing repository_name:number:index")
                    numbers.add(ref.alias.value.rsplit(":", 1)[0])
        self.timeline_pull_requests: dict[str, PullRequestRef] = {}
        if not numbers:
            return
        found: dict[str, dict[str, str]] = {}
        pending = list(numbers)
        with self.state.db.connect() as conn:
            for offset in range(0, len(pending), 50_000):
                batch = pending[offset:offset + 50_000]
                for repository_and_number, key, value in conn.execute(
                    f"""
                    SELECT composite.value, alias.key, alias.value
                    FROM ResourceAlias AS composite
                    LEFT JOIN ResourceAlias AS alias
                      ON alias.resource_id = composite.resource_id
                     AND alias.key IN ('id', 'graphql_id')
                    WHERE composite.type = 'pull_request'
                      AND composite.key = 'repository_name:number'
                      AND composite.value IN ({",".join("?" * len(batch))})
                    """,
                    batch,
                ):
                    fields = found.setdefault(repository_and_number, {})
                    if key is not None:
                        fields[key] = value
        for repository_and_number, fields in found.items():
            repository_name, number_text = repository_and_number.rsplit(":", 1)
            self.timeline_pull_requests[repository_and_number] = PullRequestRef(
                graphql_id=fields.get("graphql_id"),
                repository_name=repository_name,
                number=number_text,
                id=fields.get("id"),
            )

    def format_resource(
        self, 
        resource: ResourceRecord,
        expanded_resources_from: dict[str, list[ResourceRecord]],
        expanded_resources_to: dict[str, list[ResourceRecord]]
    ) -> User | None:
        pull_request_refs = resource.relations_to.pop("pull_requests", [])
        assigned_pull_request_refs = resource.relations_to.pop("assigned_pull_requests", [])
        review_requested_pull_request_refs = resource.relations_to.pop("review_requested_pull_requests", [])
        merged_pull_request_refs = resource.relations_to.pop("merged_pull_requests", [])
        auto_merge_pull_request_refs = resource.relations_to.pop("auto_merge_enabled_pull_requests", [])
        timeline_event_refs = resource.relations_to.pop("timeline_events", [])
        assigned_timeline_event_refs = resource.relations_to.pop("assigned_timeline_events", [])
        workflow_run_refs = resource.relations_to.pop("workflow_runs", [])
        triggered_workflow_run_refs = resource.relations_to.pop("triggered_workflow_runs", [])

        tasks = [
            format_task_reference(related_resource)
            for related_resource in expanded_resources_to.get("task_creator", [])
            if related_resource.metadata.get("unattached") != "true"
        ]

        sessions = [
            format_session_reference(related_resource)
            for related_resource in expanded_resources_to.get("session_user", [])
            if related_resource.metadata.get("unattached") != "true"
        ]

        owned_repositories = expanded_resources_to.get("repository_owner", [])
        repositories = [
            format_repository_reference(related_resource)
            for related_resource in owned_repositories
            if (
                related_resource.metadata.get("unarchived_tasks_found") != "false" or
                related_resource.metadata.get("archived_tasks_found") != "false"
            )
        ]

        if resource.found is not True:
            return None

        payload = cast(UserPayload, resource.payload)
        if "type" not in payload or not payload["type"]:
            raise ValueError("User payload is missing type")
        found_using = resource.metadata.get("found_using")
        if not found_using:
            raise ValueError("User is missing found_using")
        if "id" not in resource.aliases:
            raise ValueError("User is missing id alias")
        if "login" not in resource.aliases:
            raise ValueError("User is missing login alias")
        if "graphql_id" not in resource.aliases:
            raise ValueError("User is missing graphql_id alias")

        timeline_events = []
        for ref in timeline_event_refs:
            repository_and_number, index_text = ref.alias.value.rsplit(":", 1)
            pull_request = self.timeline_pull_requests.get(repository_and_number)
            if pull_request is None:
                raise ValueError(f"Timeline event {ref.alias.value} has no pull request")
            timeline_events.append(PullRequestTimelineReference(
                pull_request=format_pull_request_reference(pull_request),
                event_index=int(index_text),
            ))
        assigned_timeline_events = []
        for ref in assigned_timeline_event_refs:
            repository_and_number, index_text = ref.alias.value.rsplit(":", 1)
            pull_request = self.timeline_pull_requests.get(repository_and_number)
            if pull_request is None:
                raise ValueError(f"Timeline event {ref.alias.value} has no pull request")
            assigned_timeline_events.append(PullRequestTimelineReference(
                pull_request=format_pull_request_reference(pull_request),
                event_index=int(index_text),
            ))

        return User(
            id=int(resource.aliases["id"]),
            login=resource.aliases["login"].lower(),
            graphql_id=resource.aliases["graphql_id"],
            type=str(payload["type"]).lower(),
            found_using=found_using,
            repositories=repositories,
            tasks=tasks,
            sessions=sessions,
            pull_requests=[
                format_pull_request_reference(related)
                for related in pull_request_refs
            ],
            assigned_pull_requests=[
                format_pull_request_reference(related)
                for related in assigned_pull_request_refs
            ],
            review_requested_pull_requests=[
                format_pull_request_reference(related)
                for related in review_requested_pull_request_refs
            ],
            merged_pull_requests=[
                format_pull_request_reference(related)
                for related in merged_pull_request_refs
            ],
            auto_merge_enabled_pull_requests=[
                format_pull_request_reference(related)
                for related in auto_merge_pull_request_refs
            ],
            timeline_events=timeline_events,
            assigned_timeline_events=assigned_timeline_events,
            workflow_runs=[
                format_workflow_run_reference(related)
                for related in workflow_run_refs
            ],
            triggered_workflow_runs=[
                format_workflow_run_reference(related)
                for related in triggered_workflow_run_refs
            ],
            created_at=parse_utc_datetime(payload["created_at"]),
        )

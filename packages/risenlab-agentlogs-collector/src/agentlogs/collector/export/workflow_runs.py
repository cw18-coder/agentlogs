from typing import ClassVar

from agentlogs.schema import WorkflowRun
from agentlogs.schema.types.references import CheckSuiteReference, CommitReference
from ..datetime import parse_utc_datetime
from .exporter import Exporter
from .common import (
    format_optional_datetime,
    format_payload_repository_reference,
    format_repository_reference,
    format_session_reference,
    format_user_reference,
)
from ..resources import WorkflowRunRef
from ..state import Alias, ResourceRecord, ResourceRef


class WorkflowRunExporter(Exporter[WorkflowRun]):
    resource_type: ClassVar[str] = "workflow_run"
    expand_relations: ClassVar[list[str]] = [
        "repository_workflow_run",
        "session_workflow_run",
        "workflow_runs",
        "triggered_workflow_runs",
    ]

    def get_record_type(self) -> type[WorkflowRun]:
        return WorkflowRun

    def format_resource(
        self,
        resource: ResourceRecord,
        expanded_resources_from: dict[str, list[ResourceRecord]],
        expanded_resources_to: dict[str, list[ResourceRecord]]
    ) -> WorkflowRun | None:
        run = ResourceRef.from_aliases(
            resource.type,
            [Alias(key, value) for key, value in resource.aliases.items()],
        )
        if not isinstance(run, WorkflowRunRef) or run.id is None:
            raise ValueError("Workflow run is missing id")

        repositories = expanded_resources_to.get("repository_workflow_run", [])
        if len(repositories) != 1:
            raise ValueError("Workflow run must have exactly one repository")

        if resource.found is not True:
            return None
        if not isinstance(resource.payload, dict):
            raise ValueError("Workflow run payload must be a dict when found")

        sessions = [
            related
            for related in expanded_resources_to.get("session_workflow_run", [])
            if related.metadata.get("unattached") != "true"
        ]
        if len(sessions) != 1:
            raise ValueError("Workflow run must have exactly one session")

        actors = expanded_resources_from.get("workflow_runs", [])
        if len(actors) > 1:
            raise ValueError("Workflow run has more than one actor")
        triggering_actors = expanded_resources_from.get("triggered_workflow_runs", [])
        if len(triggering_actors) > 1:
            raise ValueError("Workflow run has more than one triggering actor")

        payload = resource.payload
        head_repository = format_payload_repository_reference(payload["head_repository"])
        if head_repository is None:
            raise ValueError("Workflow run payload is missing head_repository")
        check_suite_id = payload.get("check_suite_id")
        check_suite_node_id = payload.get("check_suite_node_id")
        return WorkflowRun(
            id=int(run.id),
            repository=format_repository_reference(repositories[0]),
            head_repository=head_repository,
            actor=format_user_reference(actors[0]) if actors else None,
            triggering_actor=(
                format_user_reference(triggering_actors[0]) if triggering_actors else None
            ),
            session=format_session_reference(sessions[0]),
            name=payload.get("name"),
            graphql_id=resource.aliases["graphql_id"],
            check_suite=(
                CheckSuiteReference(id=check_suite_id, graphql_id=check_suite_node_id)
                if check_suite_id is not None or check_suite_node_id is not None else
                None
            ),
            head=CommitReference(
                sha=payload["head_sha"],
                ref=payload["head_branch"] if payload.get("head_branch") not in (None, "") else None,
            ),
            path=payload["path"],
            run_number=payload["run_number"],
            run_attempt=payload.get("run_attempt"),
            event=payload["event"],
            status=payload["status"],
            conclusion=payload["conclusion"],
            workflow_id=payload["workflow_id"],
            created_at=parse_utc_datetime(payload["created_at"]),
            updated_at=parse_utc_datetime(payload["updated_at"]),
            run_started_at=format_optional_datetime(payload.get("run_started_at")),
            display_title=payload["display_title"],
        )

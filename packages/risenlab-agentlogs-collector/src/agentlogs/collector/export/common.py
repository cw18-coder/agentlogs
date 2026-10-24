import logging
from datetime import timedelta
from typing import Any, Mapping, Sequence

from agentlogs.schema import (
    AgentSessionReference,
    AgentTaskReference,
    PullRequestReference,
    RepositoryReference,
    UserReference,
    WorkflowRunReference,
)
from ..datetime import parse_utc_datetime
from ..resources import SessionRef, TaskRef
from ..state import ResourceRecord, ResourceRef

logger = logging.getLogger(__name__)

DUPLICATE_TASK_TRESHOLD = timedelta(seconds=30)

def format_resource_aliases(resource: ResourceRecord | ResourceRef) -> dict[str, str]:
    if isinstance(resource, ResourceRecord):
        return resource.aliases
    return {alias.key: alias.value for alias in resource.aliases}


def format_user_reference(resource: ResourceRecord | ResourceRef) -> UserReference:
    aliases = format_resource_aliases(resource)
    payload = resource.payload if isinstance(resource, ResourceRecord) else None
    user_type = None
    if isinstance(payload, dict) and payload.get("type"):
        user_type = str(payload["type"]).lower()
    return UserReference(
        id=int(aliases["id"]) if "id" in aliases else None,
        login=aliases["login"].lower() if "login" in aliases else None,
        graphql_id=aliases.get("graphql_id"),
        type=user_type,
    )


def format_task_reference(resource: ResourceRecord | ResourceRef) -> AgentTaskReference:
    aliases = format_resource_aliases(resource)
    if "id" not in aliases:
        raise ValueError("Task reference missing id")
    return AgentTaskReference(id=aliases["id"])


def format_session_reference(resource: ResourceRecord | ResourceRef) -> AgentSessionReference:
    aliases = format_resource_aliases(resource)
    if "id" not in aliases:
        raise ValueError("Session reference missing id")
    return AgentSessionReference(id=aliases["id"])


def format_pull_request_reference(resource: ResourceRecord | ResourceRef) -> PullRequestReference:
    aliases = format_resource_aliases(resource)
    number = None
    repository_name = None
    if "repository_name:number" in aliases:
        repository_name, number_text = aliases["repository_name:number"].rsplit(":", 1)
        number = int(number_text)
    elif isinstance(resource, ResourceRecord):
        repositories = resource.relations_to.get("repository_pull_request", [])
        if len(repositories) == 1:
            repository_name = format_resource_aliases(repositories[0]).get("full_name")
    return PullRequestReference(
        id=int(aliases["id"]) if "id" in aliases else None,
        graphql_id=aliases["graphql_id"] if "graphql_id" in aliases else None,
        number=number,
        repository=(
            RepositoryReference(full_name=repository_name)
            if repository_name is not None else
            None
        ),
    )


def format_workflow_run_reference(resource: ResourceRecord | ResourceRef) -> WorkflowRunReference:
    aliases = format_resource_aliases(resource)
    if "repository_name:id" not in aliases:
        raise ValueError("Workflow run reference missing repository_name:id")
    repository_name, run_id = aliases["repository_name:id"].rsplit(":", 1)
    return WorkflowRunReference(
        id=int(run_id),
        repository=RepositoryReference(full_name=repository_name),
    )


def format_repository_reference(resource: ResourceRecord | ResourceRef) -> RepositoryReference:
    aliases = format_resource_aliases(resource)
    if "full_name" not in aliases:
        raise ValueError("Repository reference missing full_name")
    return RepositoryReference(full_name=aliases["full_name"])


def format_optional_datetime(value: str | None) -> Any:
    if value in (None, ""):
        return None
    return parse_utc_datetime(value)


def format_payload_repository_reference(payload: dict[str, Any] | None) -> RepositoryReference | None:
    if payload is None or not payload.get("full_name"):
        return None
    return RepositoryReference(full_name=payload["full_name"].lower())


def is_duplicate_task_session(
    session: Mapping,
    task: Mapping,
    duplicate_task: Mapping,
    duplicate_task_session_ids: Sequence[str],
) -> bool:
    session_task_id = session.get("task_id")
    task_id = task.get("id")
    duplicate_task_id = duplicate_task.get("id")
    if not session_task_id or not task_id or not duplicate_task_id:
        return False
    if task_id != session_task_id or duplicate_task_id == session_task_id:
        return False
    agent_task_id = session.get("agent_task_id")
    if not agent_task_id:
        return False
    for payload in (task, duplicate_task):
        collaborator_ids = {
            item.get("agent_task_id")
            for item in payload.get("agent_collaborators") or []
            if isinstance(item, Mapping) and item.get("agent_task_id")
        }
        if collaborator_ids != {agent_task_id}:
            return False
    if task.get("state") != session.get("state"):
        return False
    if duplicate_task.get("state") not in ("queued", "in_progress"):
        return False
    if list(duplicate_task_session_ids) != [session.get("id")]:
        return False
    try:
        session_created = parse_utc_datetime(session["created_at"])
        task_created = parse_utc_datetime(task["created_at"])
        duplicate_created = parse_utc_datetime(duplicate_task["created_at"])
    except (KeyError, TypeError, ValueError):
        return False
    if task_created != session_created:
        return False
    return abs(task_created - duplicate_created) <= DUPLICATE_TASK_TRESHOLD


def warn_duplicate_task(session_id: str, task_id: str, duplicate_task_id: str) -> None:
    logger.warning(
        "session %s keeps task %s, drops task %s",
        session_id,
        task_id,
        duplicate_task_id,
    )


def find_duplicate_task_session(
    state: Any,
    session: ResourceRecord,
) -> tuple[TaskRef, TaskRef] | None:
    task_refs = [
        ref
        for ref in session.relations_to.get("task_sessions", [])
        if isinstance(ref, TaskRef)
    ]
    if len(task_refs) != 2 or not isinstance(session.payload, dict):
        return None
    records = [
        record
        for record in state.load_resources_from_refs(task_refs)
        if isinstance(record.payload, dict)
    ]
    if len(records) != 2:
        return None
    task = next(
        (
            record
            for record in records
            if record.payload.get("id") == session.payload.get("task_id")
        ),
        None,
    )
    if task is None:
        return None
    duplicate_task = next(record for record in records if record is not task)
    task_ref = next((ref for ref in task_refs if ref.id == task.aliases.get("id")), None)
    duplicate_task_ref = next((ref for ref in task_refs if ref is not task_ref), None)
    if (
        task_ref is None
        or duplicate_task_ref is None
        or task_ref.id is None
        or duplicate_task_ref.id is None
    ):
        return None
    duplicate_task_session_ids = [
        record.aliases["id"]
        for record in state.load_resources_from_refs([
            ref
            for ref in duplicate_task.relations_from.get("task_sessions", [])
            if isinstance(ref, SessionRef)
        ])
        if record.metadata.get("unattached") != "true" and record.aliases.get("id")
    ]
    if not is_duplicate_task_session(
        session.payload,
        task.payload,
        duplicate_task.payload,
        duplicate_task_session_ids,
    ):
        return None
    return task_ref, duplicate_task_ref

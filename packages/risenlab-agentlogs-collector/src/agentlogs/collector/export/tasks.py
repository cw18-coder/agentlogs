from typing import ClassVar

from agentlogs.schema import (
    AgentTask,
    AgentTaskSessionReference,
    BranchArtifactData,
    BranchReference,
    CustomAgentReference,
    AgentReference,
)
from .exporter import Exporter
from .common import (
    find_duplicate_task_session,
    format_pull_request_reference,
    format_repository_reference,
    format_user_reference,
    warn_duplicate_task,
)
from ..resources import RepositoryRef
from ..state import ResourceRecord
from ..datetime import parse_utc_datetime
    
class TaskExporter(Exporter[AgentTask]):
    resource_type: ClassVar[str] = "task"
    expand_relations: ClassVar[list[str]] = [
        "task_sessions",
        "task_creator",
        "task_pull_request",
    ]
    load_relations_for: ClassVar[list[str]] = ["pull_request"]

    def get_record_type(self) -> type[AgentTask]:
        return AgentTask

    def format_resource(
        self, 
        resource: ResourceRecord,
        expanded_resources_from: dict[str, list[ResourceRecord]],
        expanded_resources_to: dict[str, list[ResourceRecord]]
    ) -> AgentTask | None:
        if resource.metadata.get("unattached") == "true":
            return None

        if "id" not in resource.aliases:
            raise ValueError("Task is missing id alias")

        if "repository_tasks" not in resource.relations_to:
            raise ValueError("Task must have repository relation")
        
        if len(resource.relations_to["repository_tasks"]) != 1:
            raise ValueError("Task must have exactly one repository relation")

        repository_ref = resource.relations_to["repository_tasks"][0]
        if not isinstance(repository_ref, RepositoryRef):
            raise ValueError("Task repository relation is not a repository")
        repository = format_repository_reference(repository_ref)

        if resource.found is not True:
            return None

        attached_sessions = [
            related_resource
            for related_resource in expanded_resources_from.get("task_sessions", [])
            if related_resource.metadata.get("unattached") != "true"
        ]
        if len(attached_sessions) == 1:
            found = find_duplicate_task_session(self.state, attached_sessions[0])
            if found is not None:
                task, duplicate_task = found
                if duplicate_task.id == resource.aliases.get("id"):
                    warn_duplicate_task(
                        attached_sessions[0].aliases["id"],
                        task.id,
                        duplicate_task.id,
                    )
                    return None
        for related_resource in attached_sessions:
            if related_resource.metadata.get("index") is None:
                raise ValueError("Session is missing index")
            if "id" not in related_resource.aliases:
                raise ValueError("Session reference missing id")
        attached_sessions.sort(
            key=lambda related_resource: int(related_resource.metadata["index"])
        )
        sessions = [
            AgentTaskSessionReference(
                id=related_resource.aliases["id"],
                session_index=int(related_resource.metadata["index"]),
            )
            for related_resource in attached_sessions
        ]

        assert isinstance(resource.payload, dict)
        payload = resource.payload

        if (
            "task_creator" not in resource.relations_from or
            len(resource.relations_from["task_creator"]) == 0
        ):
            raise ValueError("Task must have creator")
        
        if len(resource.relations_from["task_creator"]) != 1:
            raise ValueError("Task must have exactly one creator")

        creators = expanded_resources_from.get("task_creator", [])
        if len(creators) != 1:
            raise ValueError("Task must have exactly one creator")
        creator = format_user_reference(creators[0])

        pull_request_artifacts = [
            format_pull_request_reference(related_resource)
            for related_resource in expanded_resources_from.get("task_pull_request", [])
            if related_resource.metadata.get("unattached") != "true"
        ]
        branch_artifacts: list[BranchArtifactData] = []
        for artifact in payload.get("artifacts") or []:
            if artifact["provider"] != "github":
                raise ValueError(f"Unknown artifact provider: {artifact['provider']}")
            if artifact["type"] == "github_resource":
                if artifact["data"]["type"] != "pull":
                    raise ValueError(
                        f"Unknown github_resource type: {artifact['data']['type']}"
                    )
                continue
            if artifact["type"] != "branch":
                raise ValueError(f"Unknown artifact type: {artifact['type']}")
            branch_artifacts.append(
                BranchArtifactData(
                    base=(
                        BranchReference(ref=artifact["data"]["base_ref"])
                        if "base_ref" in artifact["data"] and artifact["data"]["base_ref"] != "" else
                        None
                    ),
                    head=(
                        BranchReference(ref=artifact["data"]["head_ref"])
                        if "head_ref" in artifact["data"] and artifact["data"]["head_ref"] != "" else
                        None
                    ),
                )
            )

        return AgentTask(
            id=resource.aliases["id"],
            repository=repository,
            sessions=sessions,
            creator=creator,
            pull_request_artifacts=pull_request_artifacts,
            name=payload["name"] if payload["name"] != "" else None,
            state=payload["state"],
            archived=payload.get("archived_at") is not None,
            remote_steerable=payload["remote_steerable"],
            sharing_status=payload["sharing_status"],
            created_at=parse_utc_datetime(payload["created_at"]),
            updated_at=parse_utc_datetime(payload["updated_at"]),
            archived_at=(
                parse_utc_datetime(payload["archived_at"])
                if payload.get("archived_at") is not None else
                None
            ),
            custom_agent=CustomAgentReference(
                id=payload["custom_agent"]["id"] if "id" in payload["custom_agent"] else None,
                name=payload["custom_agent"]["name"] if "name" in payload["custom_agent"] else None,
                is_automation=(
                    payload["custom_agent"]["is_automation"]
                    if "is_automation" in payload["custom_agent"] else
                    None
                ),
            ) if "custom_agent" in payload else None,
            automation_id=payload.get("automation_id"),
            agent_collaborators=[
                AgentReference(
                    id=agent_payload["agent_id"],
                    slug=agent_payload["slug"],
                    task_id=(
                        agent_payload["agent_task_id"]
                        if "agent_task_id" in agent_payload and agent_payload["agent_task_id"] != "" else
                        None
                    ),
                    type=(
                        agent_payload["agent_type"]
                        if "agent_type" in agent_payload and agent_payload["agent_type"] != "" else
                        None
                    ),
                )
                for agent_payload in payload["agent_collaborators"]
            ],
            branch_artifacts=branch_artifacts,
        )
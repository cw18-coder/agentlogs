from dataclasses import dataclass
from typing import ClassVar

from ..state.resource import ResourceDraft, ResourceRef


@dataclass
class WorkflowRunRef(ResourceRef):
    type: ClassVar[str] = "workflow_run"
    alias_hierarchy: ClassVar[list[str]] = ["graphql_id", "repository_name:id"]
    graphql_id: str | None = None
    repository_name: str | None = None
    id: str | None = None


@dataclass
class WorkflowRunDraft(WorkflowRunRef, ResourceDraft):
    pass

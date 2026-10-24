from dataclasses import dataclass
from typing import ClassVar

from ..state.resource import ResourceDraft, ResourceRef


@dataclass
class TaskRef(ResourceRef):
    type: ClassVar[str] = "task"
    alias_hierarchy: ClassVar[list[str]] = ["id"]
    id: str | None = None


@dataclass
class TaskDraft(TaskRef, ResourceDraft):
    pass

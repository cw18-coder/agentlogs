from dataclasses import dataclass
from typing import ClassVar

from ..state.resource import ResourceDraft, ResourceRef


@dataclass
class SessionRef(ResourceRef):
    type: ClassVar[str] = "session"
    alias_hierarchy: ClassVar[list[str]] = ["id"]
    id: str | None = None


@dataclass
class SessionDraft(SessionRef, ResourceDraft):
    pass

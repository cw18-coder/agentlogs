from dataclasses import dataclass
from typing import ClassVar

from ..state.resource import ResourceDraft, ResourceRef


@dataclass
class SessionLogRef(ResourceRef):
    type: ClassVar[str] = "session_log"
    alias_hierarchy: ClassVar[list[str]] = ["id"]
    id: str | None = None


@dataclass
class SessionLogDraft(SessionLogRef, ResourceDraft):
    pass

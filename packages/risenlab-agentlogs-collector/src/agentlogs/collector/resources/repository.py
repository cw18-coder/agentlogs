from dataclasses import dataclass
from typing import ClassVar

from ..state.resource import ResourceDraft, ResourceRef


@dataclass
class RepositoryRef(ResourceRef):
    type: ClassVar[str] = "repository"
    alias_hierarchy: ClassVar[list[str]] = ["full_name"]
    full_name: str | None = None


@dataclass
class RepositoryDraft(RepositoryRef, ResourceDraft):
    pass

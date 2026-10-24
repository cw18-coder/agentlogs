from dataclasses import dataclass
from typing import ClassVar

from ..state.resource import ResourceDraft, ResourceRef


@dataclass
class UserRef(ResourceRef):
    type: ClassVar[str] = "user"
    alias_hierarchy: ClassVar[list[str]] = ["graphql_id", "id", "login"]
    graphql_id: str | None = None
    id: str | None = None
    login: str | None = None


@dataclass
class UserDraft(UserRef, ResourceDraft):
    pass

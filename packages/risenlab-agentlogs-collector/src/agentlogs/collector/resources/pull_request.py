from dataclasses import dataclass
from typing import ClassVar

from ..state.resource import ResourceDraft, ResourceRef


@dataclass
class PullRequestRef(ResourceRef):
    type: ClassVar[str] = "pull_request"
    alias_hierarchy: ClassVar[list[str]] = ["graphql_id", "repository_name:number", "id"]
    graphql_id: str | None = None
    repository_name: str | None = None
    number: str | None = None
    id: str | None = None


@dataclass
class PullRequestDraft(PullRequestRef, ResourceDraft):
    pass

from dataclasses import dataclass
from typing import ClassVar

from ..state.resource import ResourceDraft, ResourceRef


@dataclass
class PullRequestTimelineRef(ResourceRef):
    type: ClassVar[str] = "pull_request_timeline"
    alias_hierarchy: ClassVar[list[str]] = ["repository_name:number"]
    repository_name: str | None = None
    number: str | None = None


@dataclass
class PullRequestTimelineDraft(PullRequestTimelineRef, ResourceDraft):
    pass

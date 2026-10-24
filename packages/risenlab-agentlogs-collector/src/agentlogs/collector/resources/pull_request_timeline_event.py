from dataclasses import dataclass
from typing import ClassVar

from ..state.resource import ResourceDraft, ResourceRef


@dataclass
class PullRequestTimelineEventRef(ResourceRef):
    type: ClassVar[str] = "pull_request_timeline_event"
    alias_hierarchy: ClassVar[list[str]] = ["repository_name:number:index"]
    repository_name: str | None = None
    number: str | None = None
    index: str | None = None


@dataclass
class PullRequestTimelineEventDraft(PullRequestTimelineEventRef, ResourceDraft):
    pass

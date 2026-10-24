from dataclasses import dataclass, field
from typing import ClassVar

from ..api import GitHubRestAPI, NotFoundError
from ..priorities import COLLECT_PULL_REQUEST_TIMELINE_PAGE_PRIORITY, PRIORITIES
from ..resources import (
    PullRequestRef,
    PullRequestTimelineDraft,
    PullRequestTimelineEventDraft,
    UserDraft,
)
from ..runtime.processor import Processor, Result
from ..state import State
from ..state.job import Job, JobDraft, JobRecord
from .collect_user import ResolveUser, user_reference_draft


@dataclass
class CollectPullRequestTimelineJob(Job):
    type: ClassVar[str] = "collect_pull_request_timeline"
    priority: int = field(default=PRIORITIES["collect_pull_request_timeline"], kw_only=True)
    repository_name: str
    number: int
    page: int = 1
    events: list = field(default_factory=list)


@dataclass
class CollectPullRequestTimelineJobDraft(CollectPullRequestTimelineJob, JobDraft):
    requeue: ClassVar[bool] = False


@dataclass
class CollectPullRequestTimelineJobRecord(CollectPullRequestTimelineJob, JobRecord):
    pass


def timeline_event_resources(
    repository_name: str,
    number: int,
    events: list,
) -> tuple[list[PullRequestTimelineEventDraft], list[UserDraft]]:
    pull_request = PullRequestRef(repository_name=repository_name, number=number)
    event_drafts: list[PullRequestTimelineEventDraft] = []
    user_drafts: dict[tuple[str | None, str | None], UserDraft] = {}
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError(f"timeline event {index} is {type(event).__name__}")
        event_draft = PullRequestTimelineEventDraft(
            repository_name=repository_name,
            number=number,
            index=index,
            payload=event,
            relations_to={"pull_request_timeline_event": [pull_request]},
        )
        event_drafts.append(event_draft)
        actor = event.get("actor")
        if actor is None:
            actor = event.get("user")
        people: list[tuple[str, object]] = []
        if actor is not None:
            people.append(("timeline_events", actor))
        if event.get("assignee") is not None:
            people.append(("assigned_timeline_events", event.get("assignee")))
        for relation_type, reference in people:
            draft = user_reference_draft(
                reference,
                relations_to={relation_type: [event_draft]},
            )
            key = (draft.id, draft.graphql_id)
            existing = user_drafts.get(key)
            if existing is None:
                user_drafts[key] = draft
                continue
            related = existing.relations_to.setdefault(relation_type, [])
            if event_draft not in related:
                related.append(event_draft)
    return event_drafts, list(user_drafts.values())


class CollectPullRequestTimeline(Processor[CollectPullRequestTimelineJobRecord]):
    job_class = CollectPullRequestTimelineJobRecord

    def __init__(self, github_api: GitHubRestAPI, state: State):
        self.github_api = github_api
        self.state = state

    async def run(self, job: CollectPullRequestTimelineJobRecord) -> Result:
        try:
            batch = await self.github_api.request_issue_timeline(
                job.repository_name,
                job.number,
                page=job.page,
            )
        except NotFoundError:
            if job.page == 1:
                return Result(
                    resources=[
                        PullRequestTimelineDraft(
                            repository_name=job.repository_name,
                            number=job.number,
                            found=False,
                        )
                    ]
                )
            batch = []

        events = job.events + batch

        if len(batch) >= 100:
            return Result(
                continue_job=CollectPullRequestTimelineJobDraft(
                    repository_name=job.repository_name,
                    number=job.number,
                    page=job.page + 1,
                    events=events,
                    priority=COLLECT_PULL_REQUEST_TIMELINE_PAGE_PRIORITY,
                )
            )

        seen = set()
        timeline = []
        for event in events:
            if not isinstance(event, dict):
                continue
            key = (
                ("id", event["id"])
                if "id" in event and event["id"] not in (0, None) else
                ("node_id", event["node_id"])
                if "node_id" in event and event["node_id"] != "" else
                None
            )
            if key is not None and key in seen:
                continue
            if key is not None:
                seen.add(key)
            timeline.append(event)

        timeline_draft = PullRequestTimelineDraft(
            repository_name=job.repository_name,
            number=job.number,
            payload=timeline,
        )
        event_drafts, user_drafts = timeline_event_resources(
            job.repository_name,
            job.number,
            timeline,
        )
        return Result(
            resources=[
                timeline_draft,
                *event_drafts,
                *user_drafts,
            ],
            jobs=list(ResolveUser.next_jobs(user_drafts)),
            cancel_jobs=list(ResolveUser.obsolete_jobs(user_drafts)),
        )

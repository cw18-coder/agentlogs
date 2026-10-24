from dataclasses import dataclass, field
from typing import ClassVar

from ..api import GitHubRestAPI, NotFoundError
from ..datetime import get_utc_datetime
from ..priorities import COLLECT_REPOSITORY_TASKS_PAGE_PRIORITY, PRIORITIES
from ..resources import RepositoryDraft, RepositoryRef, TaskDraft, TaskRef, UserDraft
from ..runtime.processor import Processor, Result
from ..state import JobDraft
from ..state.job import Job, JobDraft as JobDraftBase, JobRecord
from .collect_task import CollectTaskJobDraft
from .collect_user import ResolveUser


@dataclass
class CollectRepositoryTasksJob(Job):
    type: ClassVar[str] = "collect_repository_tasks"
    priority: int = field(default=PRIORITIES["collect_repository_tasks"], kw_only=True)
    repository_name: str
    updated_since: str | None = None


@dataclass
class CollectRepositoryTasksJobDraft(CollectRepositoryTasksJob, JobDraftBase):
    requeue: ClassVar[bool] = False


@dataclass
class CollectRepositoryTasksJobRecord(CollectRepositoryTasksJob, JobRecord):
    pass


@dataclass
class CollectRepositoryTasksArchivedJob(CollectRepositoryTasksJob):
    type: ClassVar[str] = "collect_repository_tasks_archived"


@dataclass
class CollectRepositoryTasksArchivedJobDraft(CollectRepositoryTasksArchivedJob, JobDraftBase):
    requeue: ClassVar[bool] = False


@dataclass
class CollectRepositoryTasksArchivedJobRecord(CollectRepositoryTasksArchivedJob, JobRecord):
    pass


class CollectRepositoryTasks(Processor[CollectRepositoryTasksJobRecord]):
    job_class = CollectRepositoryTasksJobRecord

    github_api: GitHubRestAPI

    def __init__(self, github_api: GitHubRestAPI):
        self.github_api = github_api

    def handled_types(self) -> list[str]:
        return [
            CollectRepositoryTasksJobRecord.type,
            CollectRepositoryTasksArchivedJobRecord.type,
        ]

    async def run(self, job: CollectRepositoryTasksJob) -> Result:
        since = job.updated_since or get_utc_datetime(1, 1, 2000).replace(tzinfo=None).isoformat() + 'Z'
        page_size = 50
        archived = job.type == CollectRepositoryTasksArchivedJob.type
        draft_class = (
            CollectRepositoryTasksArchivedJobDraft
            if archived else
            CollectRepositoryTasksJobDraft
        )

        try:
            tasks = await self.github_api.request_tasks(job.repository_name, archived, since, page_size)
        except NotFoundError:
            if job.updated_since is not None:
                return Result()
            return Result(
                resources=[
                    RepositoryDraft(
                        full_name=job.repository_name,
                        metadata=(
                            {"archived_tasks_found": "false"}
                            if archived else
                            {"unarchived_tasks_found": "false"}
                        )
                    )
                ]
            )

        owner_login = job.repository_name.split("/", 1)[0]
        owner = UserDraft(
            login=owner_login,
            relations_to={
                "repository_owner": [
                    RepositoryRef(full_name=job.repository_name)
                ]
            },
        )
        follow_up: list[JobDraft] = [
            CollectTaskJobDraft(
                task_id=task["id"],
                repository_name=job.repository_name,
                resource=TaskRef(id=task["id"]),
            )
            for task in tasks
        ]
        follow_up.extend(ResolveUser.next_jobs(owner))
        cancels = ResolveUser.obsolete_jobs(owner)
        continue_job = None
        if len(tasks) >= page_size and tasks[-1]["updated_at"] != since:
            continue_job = draft_class(
                repository_name=job.repository_name,
                updated_since=tasks[-1]["updated_at"],
                priority=COLLECT_REPOSITORY_TASKS_PAGE_PRIORITY,
            )

        return Result(
            jobs=follow_up,
            cancel_jobs=cancels,
            continue_job=continue_job,
            resources=[
                TaskDraft(
                    id=task["id"],
                    relations_to={
                        "repository_tasks": [
                            RepositoryRef(full_name=job.repository_name)
                        ]
                    },
                ) for task in tasks
            ] + [owner]
        )

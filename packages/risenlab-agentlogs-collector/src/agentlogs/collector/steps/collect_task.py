from dataclasses import dataclass, field
from typing import ClassVar
from urllib.parse import urlparse

from ..api import CopilotRestAPI, NotFoundError
from ..datetime import parse_utc_datetime
from ..priorities import PRIORITIES
from ..resources import (
    PullRequestDraft,
    RepositoryRef,
    SessionDraft,
    SessionLogDraft,
    SessionLogRef,
    SessionRef,
    TaskDraft,
    TaskRef,
    WorkflowRunDraft,
    WorkflowRunRef,
)
from ..runtime.processor import Processor, Result
from ..state.job import Job, JobDraft, JobRecord
from .collect_pull_request import ResolvePullRequest
from .collect_session_log import CollectSessionLogJobDraft
from .collect_user import ResolveUser, user_reference_draft
from .collect_workflow_run import CollectWorkflowRunJobDraft


@dataclass
class CollectTaskJob(Job):
    type: ClassVar[str] = "collect_task"
    priority: int = field(default=PRIORITIES["collect_task"], kw_only=True)
    task_id: str
    repository_name: str


@dataclass
class CollectTaskJobDraft(CollectTaskJob, JobDraft):
    pass


@dataclass
class CollectTaskJobRecord(CollectTaskJob, JobRecord):
    pass


class CollectTask(Processor[CollectTaskJobRecord]):
    job_class = CollectTaskJobRecord

    copilot_api: CopilotRestAPI

    def __init__(self, copilot_api: CopilotRestAPI):
        self.copilot_api = copilot_api

    async def run(self, job: CollectTaskJobRecord) -> Result:
        try:
            task = await self.copilot_api.request_task_detailed(job.task_id)
        except NotFoundError:
            return Result(
                resources=[
                    TaskDraft(
                        id=job.task_id,
                        found=False,
                    )
                ]
            )

        sessions = task.pop("sessions") if "sessions" in task else []
        environment = task.get("current_environment")
        task_is_unattached = environment is not None
        user_drafts = []
        for session in sessions:
            user_drafts.append(user_reference_draft(
                session["user"],
                relations_to={
                    "session_user": [SessionRef(id=session["id"])]
                },
            ))
        user_drafts.append(user_reference_draft(
            task["creator"],
            relations_to={
                "task_creator": [TaskRef(id=job.task_id)]
            },
        ))
        follow_up = [
            CollectSessionLogJobDraft(
                session_id=session["id"],
                resource=SessionLogRef(id=session["id"]),
            )
            for session in sessions
            if not task_is_unattached and not session_is_unattached(session)
        ]
        run_drafts = []
        for session in sessions:
            workflow_run_id = session.get("workflow_run_id")
            if workflow_run_id in (0, None):
                continue
            run_drafts.append(
                WorkflowRunDraft(
                    id=workflow_run_id,
                    repository_name=job.repository_name,
                    relations_to={
                        "repository_workflow_run": [
                            RepositoryRef(full_name=job.repository_name)
                        ],
                        "session_workflow_run": [SessionRef(id=session["id"])],
                    },
                )
            )
            follow_up.append(
                CollectWorkflowRunJobDraft(
                    repository_name=job.repository_name,
                    workflow_run_id=int(workflow_run_id),
                    resource=WorkflowRunRef(
                        id=workflow_run_id,
                        repository_name=job.repository_name,
                    ),
                )
            )
        cancels = list(ResolveUser.obsolete_jobs(user_drafts))
        follow_up.extend(ResolveUser.next_jobs(user_drafts))
        pull_request_drafts = []
        for artifact in task.get("artifacts") or []:
            if artifact.get("type") != "github_resource":
                continue
            data = artifact.get("data") or {}
            if data.get("type") != "pull":
                continue
            repository_name = repository_name_from_pull_url(
                data.get("url") or data.get("html_url"),
                job.repository_name,
            )
            draft = pull_request_draft(
                rest_id=data.get("id"),
                global_id=data.get("global_id"),
                number=data.get("number"),
                repository_name=repository_name,
                relations_to={
                    "task_pull_request": [TaskRef(id=job.task_id)],
                    "repository_pull_request": [
                        RepositoryRef(full_name=repository_name)
                    ],
                },
            )
            if draft is None:
                continue
            pull_request_drafts.append(draft)
        for session in sessions:
            draft = pull_request_draft(
                rest_id=session.get("resource_id"),
                global_id=session.get("resource_global_id"),
                number=session.get("resource_number"),
                repository_name=job.repository_name,
                relations_to={
                    "session_pull_request": [SessionRef(id=session["id"])],
                    "repository_pull_request": [
                        RepositoryRef(full_name=job.repository_name)
                    ],
                },
            )
            if draft is None:
                continue
            pull_request_drafts.append(draft)
        follow_up.extend(ResolvePullRequest.next_jobs(pull_request_drafts))
        cancels.extend(ResolvePullRequest.obsolete_jobs(pull_request_drafts))
        task_metadata: dict[str, str] = {}
        if task_is_unattached or (
            sessions and all(session_is_unattached(session) for session in sessions)
        ):
            task_metadata["unattached"] = "true"
        ordered_sessions = [
            session
            for _, session in sorted(
                enumerate(sessions),
                key=lambda item: (
                    parse_utc_datetime(item[1]["created_at"]),
                    item[0],
                ),
            )
        ]
        session_drafts = []
        for index, session in enumerate(ordered_sessions):
            unattached = task_is_unattached or session_is_unattached(session)
            metadata = {"index": str(index)}
            if index:
                metadata["previous_session_id"] = ordered_sessions[index - 1]["id"]
            if index + 1 < len(ordered_sessions):
                metadata["next_session_id"] = ordered_sessions[index + 1]["id"]
            if unattached:
                metadata["unattached"] = "true"
            session_drafts.append(
                SessionDraft(
                    id=session["id"],
                    payload=session,
                    metadata=metadata,
                    relations_to={
                        "task_sessions": [TaskRef(id=job.task_id)]
                    },
                )
            )
        return Result(
            jobs=follow_up,
            cancel_jobs=cancels,
            resources=session_drafts + [
                SessionLogDraft(
                    id=session["id"],
                    relations_to={
                        "session_session_log": [SessionRef(id=session["id"])]
                    },
                ) for session in sessions
                if not task_is_unattached and not session_is_unattached(session)
            ] + [
                TaskDraft(
                    id=job.task_id,
                    payload=task,
                    metadata=task_metadata,
                )
            ] + user_drafts + run_drafts + pull_request_drafts
        )


def session_is_unattached(session: dict) -> bool:
    return session.get("environment_id") is not None or (
        session.get("workflow_run_id") in (0, None)
        and session.get("resource_id") in (0, None)
        and session.get("event_type") in (None, "", "agent_tasks_api")
    )


def repository_name_from_pull_url(url: str | None, fallback: str) -> str:
    if not url:
        return fallback
    path = urlparse(url).path.strip("/").split("/")
    if len(path) >= 2:
        return f"{path[0]}/{path[1]}".lower()
    return fallback


def pull_request_draft(
    rest_id: object,
    global_id: object,
    number: object,
    repository_name: str,
    relations_to: dict,
) -> PullRequestDraft | None:
    if rest_id in (0, None):
        rest_id = None
    if number in (0, None):
        number = None
    if global_id in (None, ""):
        global_id = None
    if rest_id is None and number is None and global_id is None:
        return None
    return PullRequestDraft(
        id=rest_id,
        graphql_id=global_id,
        number=number,
        repository_name=repository_name,
        relations_to=relations_to,
    )

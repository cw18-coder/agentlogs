from dataclasses import dataclass, field
from typing import ClassVar

from ..api import GitHubRestAPI, NotFoundError
from ..priorities import PRIORITIES
from ..resources import UserDraft, WorkflowRunDraft
from ..runtime.processor import Processor, Result
from ..state.job import Job, JobDraft, JobRecord
from .collect_user import ResolveUser, user_reference_draft


@dataclass
class CollectWorkflowRunJob(Job):
    type: ClassVar[str] = "collect_workflow_run"
    priority: int = field(default=PRIORITIES["collect_workflow_run"], kw_only=True)
    repository_name: str
    workflow_run_id: int


@dataclass
class CollectWorkflowRunJobDraft(CollectWorkflowRunJob, JobDraft):
    pass


@dataclass
class CollectWorkflowRunJobRecord(CollectWorkflowRunJob, JobRecord):
    pass


class CollectWorkflowRun(Processor[CollectWorkflowRunJobRecord]):
    job_class = CollectWorkflowRunJobRecord

    github_api: GitHubRestAPI

    def __init__(self, github_api: GitHubRestAPI):
        self.github_api = github_api

    async def run(self, job: CollectWorkflowRunJobRecord) -> Result:
        try:
            run = await self.github_api.request_workflow_run(
                job.repository_name,
                job.workflow_run_id,
            )
        except NotFoundError:
            return Result(
                resources=[
                    WorkflowRunDraft(
                        id=job.workflow_run_id,
                        repository_name=job.repository_name,
                        found=False,
                    )
                ]
            )
        repository_name = run["repository"]["full_name"].lower()
        if repository_name != job.repository_name:
            raise ValueError(
                f"workflow run repository {repository_name} does not match "
                f"job repository {job.repository_name}"
            )
        workflow_run = WorkflowRunDraft(
            id=run["id"],
            repository_name=repository_name,
            graphql_id=run["node_id"],
            payload=run,
        )
        references = [
            ("workflow_runs", run.get("actor")),
            ("triggered_workflow_runs", run.get("triggering_actor")),
        ]
        user_drafts: list[UserDraft] = []
        for relation_type, reference in references:
            if reference is None:
                continue
            user_drafts.append(user_reference_draft(
                reference,
                relations_to={relation_type: [workflow_run]},
            ))
        return Result(
            resources=[
                workflow_run,
                *user_drafts,
            ],
            jobs=list(ResolveUser.next_jobs(user_drafts)),
            cancel_jobs=list(ResolveUser.obsolete_jobs(user_drafts)),
        )

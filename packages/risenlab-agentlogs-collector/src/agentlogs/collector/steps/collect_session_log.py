from dataclasses import dataclass, field
from typing import ClassVar

from ..api import CopilotRestAPI, NotFoundError
from ..priorities import PRIORITIES
from ..resources import SessionLogDraft
from ..runtime.processor import Processor, Result
from ..state.job import Job, JobDraft, JobRecord


@dataclass
class CollectSessionLogJob(Job):
    type: ClassVar[str] = "collect_session_log"
    priority: int = field(default=PRIORITIES["collect_session_log"], kw_only=True)
    session_id: str


@dataclass
class CollectSessionLogJobDraft(CollectSessionLogJob, JobDraft):
    pass


@dataclass
class CollectSessionLogJobRecord(CollectSessionLogJob, JobRecord):
    pass


class CollectSessionLog(Processor[CollectSessionLogJobRecord]):
    job_class = CollectSessionLogJobRecord

    copilot_api: CopilotRestAPI

    def __init__(self, copilot_api: CopilotRestAPI):
        self.copilot_api = copilot_api

    async def run(self, job: CollectSessionLogJobRecord) -> Result:
        try:
            log = await self.copilot_api.request_session_log(job.session_id)
        except NotFoundError:
            return Result(
                resources=[
                    SessionLogDraft(
                        id=job.session_id,
                        found=False,
                    )
                ],
            )

        return Result(
            resources=[
                SessionLogDraft(
                    id=job.session_id,
                    payload=log,
                )
            ],
        )

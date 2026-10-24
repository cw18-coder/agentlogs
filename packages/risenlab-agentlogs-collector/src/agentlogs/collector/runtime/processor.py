from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from ..state import JobDraft, JobRecord, ResourceDraft


@dataclass
class Result:
    jobs: list[JobDraft] | None = None
    resources: list[ResourceDraft] | None = None
    cancel_jobs: list[JobDraft] | None = None
    continue_job: JobDraft | None = None


J = TypeVar("J", bound=JobRecord)
class Processor(ABC, Generic[J]):
    job_class: type[J]

    def handled_types(self) -> list[str]:
        return [self.job_class.type]

    async def process(self, job: JobRecord) -> Result:
        if job.type not in self.handled_types():
            raise TypeError(
                f"{type(self).__name__} does not handle {job.type!r}"
            )
        return await self.run(job)

    @abstractmethod
    async def run(self, job: J) -> Result:
        raise NotImplementedError()

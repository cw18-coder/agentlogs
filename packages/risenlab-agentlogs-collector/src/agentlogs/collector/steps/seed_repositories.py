import asyncio
import csv
import json
from dataclasses import dataclass, field
from typing import ClassVar

from ..priorities import PRIORITIES
from ..resources import RepositoryDraft, RepositoryRef
from ..runtime.processor import Processor, Result
from ..state import JobDraft
from ..state.job import Job, JobDraft as JobDraftBase, JobRecord
from .collect_repository_tasks import (
    CollectRepositoryTasksArchivedJobDraft,
    CollectRepositoryTasksJobDraft,
)


@dataclass
class SeedRepositoriesJob(Job):
    type: ClassVar[str] = "seed_repositories"
    priority: int = field(default=PRIORITIES["seed_repositories"], kw_only=True)
    offset: int = 0


@dataclass
class SeedRepositoriesJobDraft(SeedRepositoriesJob, JobDraftBase):
    pass


@dataclass
class SeedRepositoriesJobRecord(SeedRepositoriesJob, JobRecord):
    pass


class SeedRepositories(Processor[SeedRepositoriesJobRecord]):
    job_class = SeedRepositoriesJobRecord

    csv_path: str
    chunk_size: int

    def __init__(self, csv_path: str, chunk_size: int):
        self.csv_path = csv_path
        self.chunk_size = chunk_size

    def read_csv_chunk(self, offset: int) -> tuple[list[dict[str, object]], int] | None:
        with open(self.csv_path, "rb") as raw:
            header = raw.readline()
            if not header:
                return None
            columns = next(csv.reader([header.decode()]))
            if offset:
                raw.seek(offset)
            pos = raw.tell()

            def lines():
                nonlocal pos
                while True:
                    line = raw.readline()
                    if not line:
                        return
                    pos += len(line)
                    yield line.decode()

            rows: list[dict[str, object]] = []
            for row in csv.DictReader(lines(), fieldnames=columns):
                rows.append(row)
                if len(rows) == self.chunk_size:
                    break
        if not rows:
            return None
        for row in rows:
            row.pop("id", None)
            row.pop(None, None)
            row["metrics"] = json.loads(row["metrics"]) if row.get("metrics") else {}
            row["languages"] = json.loads(row["languages"]) if row.get("languages") else {}
            row["labels"] = row["labels"].split(";") if row.get("labels") else []
            row["topics"] = row["topics"].split(";") if row.get("topics") else []
        return rows, pos

    async def run(self, job: SeedRepositoriesJobRecord) -> Result:
        loaded = await asyncio.to_thread(self.read_csv_chunk, job.offset)

        if loaded is None:
            return Result()

        rows, next_offset = loaded
        follow_up: list[JobDraft] = []
        for repository in rows:
            name = str(repository["name"]).lower()
            follow_up.append(
                CollectRepositoryTasksJobDraft(
                    repository_name=name,
                    resource=RepositoryRef(full_name=name),
                )
            )
            follow_up.append(
                CollectRepositoryTasksArchivedJobDraft(
                    repository_name=name,
                    resource=RepositoryRef(full_name=name),
                )
            )

        return Result(
            jobs=follow_up,
            continue_job=SeedRepositoriesJobDraft(offset=next_offset),
            resources=[
                RepositoryDraft(
                    full_name=str(repository["name"]).lower(),
                    payload=repository,
                ) for repository in rows
            ]
        )

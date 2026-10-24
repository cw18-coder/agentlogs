from dataclasses import dataclass

from .job import JobStatus
from .storage import Database

@dataclass
class JobStatusCount:
    queued: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    canceled: int = 0

    @property
    def total(self) -> int:
        return (
            self.queued
            + self.running
            + self.completed
            + self.failed
            + self.canceled
        )
    
    @property
    def done(self) -> int:
        return self.completed + self.failed + self.canceled

class Progress:
    db: Database
    
    job_status_counts: dict[str, JobStatusCount] = {}
    resource_counts: dict[str, int] = {}
    resource_not_found_counts: dict[str, int] = {}
    resource_found_counts: dict[str, int] = {}

    def __init__(self, db: Database):
        self.db = db

    def initialize(self) -> None:
        self.job_status_counts = self.query_job_status_counts()
        self.resource_counts = self.query_resource_counts()
        (
            self.resource_not_found_counts,
            self.resource_found_counts,
        ) = self.query_resource_found_counts()

    def query_resource_counts(self) -> dict[str, int]:
        with self.db.connect() as conn:
            rows = conn.execute(
"""
SELECT type, COUNT(*)
FROM Resource
GROUP BY type;
"""
            ).fetchall()
        return {resource_type: count for resource_type, count in rows}

    def query_resource_found_counts(self) -> tuple[dict[str, int], dict[str, int]]:
        with self.db.connect() as conn:
            rows = conn.execute(
"""
SELECT type, SUM(found = 1), SUM(found = 0)
FROM Resource
GROUP BY type;
"""
            ).fetchall()
        not_found_counts = {
            resource_type: int(not_found or 0)
            for resource_type, _, not_found in rows
        }
        found_counts = {
            resource_type: int(found or 0)
            for resource_type, found, _ in rows
        }
        return not_found_counts, found_counts

    def query_job_status_counts(self) -> dict[str, JobStatusCount]:
        job_status_counts: dict[str, JobStatusCount] = {}

        with self.db.connect() as conn:
            rows = conn.execute(
"""
SELECT type, status, COUNT(*)
FROM Job
GROUP BY type, status;
"""
            ).fetchall()

        for job_type, status, count in rows:
            if job_type not in job_status_counts:
                job_status_counts[job_type] = JobStatusCount()

            job_status_counts[job_type].__dict__[status] = count

        return job_status_counts
    
    def get_job_type_status_counts(self, job_type: str) -> JobStatusCount:
        if job_type not in self.job_status_counts:
            self.job_status_counts[job_type] = JobStatusCount()

        return self.job_status_counts[job_type]
    
    def get_job_types_status_counts(self, job_types: list[str]) -> JobStatusCount:
        if len(job_types) == 0:
            return JobStatusCount()
        
        if len(job_types) == 1:
            return self.get_job_type_status_counts(job_types[0])
        
        return JobStatusCount(**{
            status: sum(self.get_job_type_status_counts(job_type).__dict__[status] for job_type in job_types)
            for status in ["queued", "running", "completed", "failed", "canceled"]
        })
    
    def mutate_job_status_update(self, job_type: str, from_status: JobStatus, to_status: JobStatus) -> None:
        if job_type not in self.job_status_counts:
            return

        self.job_status_counts[job_type].__dict__[from_status] -= 1
        self.job_status_counts[job_type].__dict__[to_status] += 1

    def mutate_job_status_create(self, job_type: str) -> None:
        if job_type not in self.job_status_counts:
            self.job_status_counts[job_type] = JobStatusCount()

        self.job_status_counts[job_type].queued += 1

    def mutate_resource_create(self, resource_type: str) -> None:
        self.resource_counts[resource_type] = self.resource_counts.get(resource_type, 0) + 1

    def mutate_resource_delete(self, resource_type: str, count: int = 1) -> None:
        self.resource_counts[resource_type] = self.resource_counts.get(resource_type, 0) - count

    def mutate_resource_not_found_create(self, resource_type: str) -> None:
        self.resource_not_found_counts[resource_type] = self.resource_not_found_counts.get(resource_type, 0) + 1

    def mutate_resource_not_found_delete(self, resource_type: str, count: int = 1) -> None:
        self.resource_not_found_counts[resource_type] = self.resource_not_found_counts.get(resource_type, 0) - count

    def mutate_resource_found_create(self, resource_type: str) -> None:
        self.resource_found_counts[resource_type] = self.resource_found_counts.get(resource_type, 0) + 1

    def mutate_resource_found_delete(self, resource_type: str, count: int = 1) -> None:
        self.resource_found_counts[resource_type] = self.resource_found_counts.get(resource_type, 0) - count


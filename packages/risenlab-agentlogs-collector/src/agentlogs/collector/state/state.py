import json
from typing import Sequence

from .job import JobDraft, JobRecord
from .progress import Progress
from .queue_state import QueueState
from .resource import ResourceDraft
from .resource_state import ResourceState
from .storage import Database, PayloadStorage


class State(QueueState, ResourceState):
    def __init__(self, db: Database, payload_storage: PayloadStorage):
        self.db = db
        self.payload_storage = payload_storage
        self.progress = Progress(db)
        self.queue_generation = 1

    def complete_job(
        self, 
        job: JobRecord,
        jobs: list[JobDraft] | None = None, 
        resources: Sequence[ResourceDraft] | None = None,
        cancel_jobs: Sequence[JobDraft] | None = None,
        continue_job: JobDraft | None = None,
    ) -> None:
        with self.db.connect() as conn:
            status, = conn.execute(
"""
SELECT status FROM Job WHERE id = :id
""",
                {"id": job.id},
            ).fetchone()
            if status != "running":
                return

            if resources is not None:
                self.save_resources(resources, conn=conn)

            if cancel_jobs:
                self.cancel_queued_jobs(cancel_jobs, conn=conn)

            if jobs:
                self.create_jobs(jobs, conn=conn)

            if continue_job is not None:
                if continue_job.type != job.type:
                    raise ValueError(
                        f"continue_job type {continue_job.type!r} does not match {job.type!r}"
                    )
                if continue_job.resource is not None:
                    resource_id = self.resolve_refs([continue_job.resource], conn=conn)[0]
                    if resource_id != job.resource_id:
                        raise ValueError(
                            f"continue_job resource {resource_id} does not match job resource {job.resource_id}"
                        )
                conn.execute(
"""
UPDATE Job
SET status = 'queued',
    priority = :priority,
    parameters = :parameters,
    error = NULL,
    updated_at = CURRENT_TIMESTAMP
WHERE id = :id
""",
                    {
                        "id": job.id,
                        "priority": continue_job.priority,
                        "parameters": json.dumps(continue_job.get_parameters()),
                    },
                )
                self.progress.mutate_job_status_update(
                    job.type,
                    from_status="running",
                    to_status="queued",
                )
                self.queue_generation += 1
            else:
                self.update_job_status(job, status="completed", conn=conn)

from contextlib import nullcontext
import json
import sqlite3
from typing import Sequence

from .job import Job, JobDraft, JobRecord, JobStatus
from .progress import Progress
from .resource_state import SQLITE_VAR_LIMIT
from .storage import Database


class QueueState:
    db: Database
    progress: Progress
    queue_generation: int = 1

    def claim_job(
        self,
        types: list[str] | None = None,
        *,
        type_groups: list[list[str]] | None = None,
    ) -> JobRecord | None:
        if types is not None and type_groups is not None:
            raise ValueError("pass types or type_groups, not both")
        if type_groups is None:
            if types is None or len(types) == 0:
                return None
            type_groups = [types]
        type_groups = [group for group in type_groups if group]
        if not type_groups:
            return None

        with self.db.connect(immediate=True) as conn:
            row = None
            for group in type_groups:
                for job_type in group:
                    candidate = conn.execute(
"""
SELECT id, type, priority, parameters, resource_id
FROM Job INDEXED BY "Job.queue"
WHERE status = 'queued' AND type = ?
ORDER BY priority DESC, id ASC
LIMIT 1
""",
                        (job_type,),
                    ).fetchone()
                    if candidate is None:
                        continue
                    if row is None or candidate[2] > row[2] or (
                        candidate[2] == row[2] and candidate[0] < row[0]
                    ):
                        row = candidate
                if row is not None:
                    break

            if row is None:
                return None
            
            id, job_type, priority, parameters, resource_id = row
            try:
                job_class = JobRecord._registry[job_type]
            except KeyError:
                raise ValueError(f"Unknown job type: {job_type}")
            job = job_class(
                id=id,
                status="running",
                priority=priority,
                resource_id=resource_id,
                **json.loads(parameters),
            )

            self.update_job_status(job, status="running", conn=conn)

        return job

    def fail_job(self, job: JobRecord, error: str) -> None:
        with self.db.connect() as conn:
            self.update_job_status(
                job,
                status="failed",
                error=error,
                conn=conn
            )

    def retry_job(self, job: JobRecord, error: str) -> None:
        with self.db.connect() as conn:
            self.update_job_status(
                job,
                status="queued",
                error=error,
                conn=conn
            )

    def reset_job(self, job: JobRecord) -> None:
        with self.db.connect() as conn:
            self.update_job_status(
                job,
                status="queued",
                error=None,
                conn=conn
            )

    def cancel_job(self, job: JobRecord, conn: sqlite3.Connection | None = None) -> None:
        cm = nullcontext(conn) if conn is not None else self.db.connect()

        with cm as conn:
            self.update_job_status(
                job,
                status="canceled",
                conn=conn
            )

    def update_job_status(
        self, 
        job: JobRecord, 
        status: JobStatus, 
        error: str | None = None,
        conn: sqlite3.Connection | None = None
    ) -> None:
        cm = nullcontext(conn) if conn is not None else self.db.connect()

        with cm as conn:
            old_status, = conn.execute(
"""
SELECT status FROM Job WHERE id = :id;
""",
                {"id": job.id}
            ).fetchone()

            conn.execute(
"""
UPDATE Job
SET status = :status, error = :error, updated_at = CURRENT_TIMESTAMP
WHERE id = :id;
""",
                {
                    "id": job.id,
                    "status": status,
                    "error": error
                }
            )

            self.progress.mutate_job_status_update(job.type, from_status=old_status, to_status=status)

        self.queue_generation += 1

    def update_job_parameters(
        self,
        job: JobRecord,
        conn: sqlite3.Connection | None = None,
    ) -> None:
        cm = nullcontext(conn) if conn is not None else self.db.connect()

        with cm as conn:
            conn.execute(
"""
UPDATE Job
SET parameters = :parameters, updated_at = CURRENT_TIMESTAMP
WHERE id = :id;
""",
                {
                    "id": job.id,
                    "parameters": json.dumps(job.get_parameters()),
                }
            )

    def load_jobs_by_type_and_resource(
        self,
        keys: Sequence[tuple[str, int]],
        conn: sqlite3.Connection,
    ) -> dict[tuple[str, int], tuple[int, str, int, str]]:
        unique_keys = list(dict.fromkeys(keys))
        if not unique_keys:
            return {}

        found: dict[tuple[str, int], tuple[int, str, int, str]] = {}
        pair_chunk = SQLITE_VAR_LIMIT // 2
        for offset in range(0, len(unique_keys), pair_chunk):
            batch = unique_keys[offset:offset + pair_chunk]
            for job_id, job_type, status, priority, parameters, resource_id in conn.execute(
f"""
SELECT id, type, status, priority, parameters, resource_id
FROM Job
WHERE (type, resource_id) IN ({",".join("(?, ?)" for _ in batch)})
""",
                [value for pair in batch for value in pair],
            ).fetchall():
                found[(job_type, resource_id)] = (job_id, status, priority, parameters)
        return found

    def create_jobs(
        self,
        jobs: Sequence[Job],
        conn: sqlite3.Connection | None = None,
    ) -> None:
        cm = nullcontext(conn) if conn is not None else self.db.connect()

        with cm as conn:
            draft_refs = [
                job.resource
                if isinstance(job, JobDraft) and job.resource is not None else
                None
                for job in jobs
            ]
            resolved_ids = iter(
                self.resolve_refs(
                    [ref for ref in draft_refs if ref is not None],
                    conn=conn,
                )
            )
            resource_ids: list[int | None] = []
            lookup_keys: list[tuple[str, int]] = []
            for job, draft_ref in zip(jobs, draft_refs):
                resource_id = None
                if draft_ref is not None:
                    resource_id = next(resolved_ids)
                elif isinstance(job, JobRecord):
                    resource_id = job.resource_id
                resource_ids.append(resource_id)
                if resource_id is not None:
                    lookup_keys.append((job.type, resource_id))
            existing_jobs = self.load_jobs_by_type_and_resource(lookup_keys, conn)

            for job, resource_id in zip(jobs, resource_ids):
                existing = (
                    existing_jobs.get((job.type, resource_id))
                    if resource_id is not None else
                    None
                )
                if existing is None:
                    parameters = json.dumps(job.get_parameters())
                    inserted = conn.execute(
"""
INSERT INTO Job (
    type, priority, parameters, status, resource_id, created_at, updated_at
)
VALUES (
    :type, :priority, :parameters, :status, :resource_id,
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT(type, resource_id) DO NOTHING
RETURNING id
""",
                        {
                            "type": job.type,
                            "priority": job.priority,
                            "parameters": parameters,
                            "status": "queued",
                            "resource_id": resource_id,
                        },
                    ).fetchone()
                    if inserted is not None:
                        self.progress.mutate_job_status_create(job.type)
                        if resource_id is not None:
                            existing_jobs[(job.type, resource_id)] = (
                                inserted[0],
                                "queued",
                                job.priority,
                                parameters,
                            )
                        continue
                    existing = self.load_jobs_by_type_and_resource(
                        [(job.type, resource_id)],
                        conn,
                    )[(job.type, resource_id)]

                existing_id, status, _, _ = existing
                if status in ("queued", "running"):
                    continue
                if (
                    isinstance(job, JobDraft)
                    and not job.requeue
                    and status in ("completed", "canceled")
                ):
                    continue
                parameters = json.dumps(job.get_parameters())
                conn.execute(
"""
UPDATE Job
SET status = 'queued',
    error = NULL,
    priority = :priority,
    parameters = :parameters,
    updated_at = CURRENT_TIMESTAMP
WHERE id = :id
""",
                    {
                        "id": existing_id,
                        "priority": job.priority,
                        "parameters": parameters,
                    },
                )
                self.progress.mutate_job_status_update(
                    job.type,
                    from_status=status,
                    to_status="queued",
                )
                existing_jobs[(job.type, resource_id)] = (
                    existing_id,
                    "queued",
                    job.priority,
                    parameters,
                )

        self.queue_generation += 1

    def remap_resource_jobs(
        self,
        from_resource_ids: Sequence[int],
        to_resource_id: int,
        conn: sqlite3.Connection | None = None,
    ) -> None:
        if not from_resource_ids:
            return

        cm = nullcontext(conn) if conn is not None else self.db.connect()

        with cm as conn:
            resource_ids = [to_resource_id, *from_resource_ids]
            jobs_by_resource: dict[int, list[tuple[int, str, str, int, str]]] = {
                resource_id: [] for resource_id in resource_ids
            }
            for job_id, job_type, status, priority, parameters, resource_id in conn.execute(
f"""
SELECT id, type, status, priority, parameters, resource_id
FROM Job
WHERE resource_id IN ({",".join("?" * len(resource_ids))})
""",
                resource_ids,
            ).fetchall():
                jobs_by_resource[resource_id].append(
                    (job_id, job_type, status, priority, parameters)
                )

            winner_by_type = {
                job_type: (job_id, status)
                for job_id, job_type, status, _, _ in jobs_by_resource[to_resource_id]
            }
            move_ids: list[int] = []
            null_ids: list[int] = []
            for loser_id in from_resource_ids:
                for job_id, job_type, status, priority, parameters in jobs_by_resource[loser_id]:
                    if status == "running":
                        null_ids.append(job_id)
                        continue

                    if job_type not in winner_by_type:
                        move_ids.append(job_id)
                        winner_by_type[job_type] = (job_id, status)
                        continue

                    if status == "queued":
                        job_class = JobRecord._registry[job_type]
                        self.cancel_job(
                            job_class(
                                id=job_id,
                                status=status,
                                priority=priority,
                                resource_id=loser_id,
                                **json.loads(parameters),
                            ),
                            conn=conn,
                        )
                    null_ids.append(job_id)

            if move_ids:
                conn.execute(
f"""
UPDATE Job
SET resource_id = ?, updated_at = CURRENT_TIMESTAMP
WHERE id IN ({",".join("?" * len(move_ids))})
""",
                    [to_resource_id, *move_ids],
                )
            if null_ids:
                conn.execute(
f"""
UPDATE Job
SET resource_id = NULL, updated_at = CURRENT_TIMESTAMP
WHERE id IN ({",".join("?" * len(null_ids))})
""",
                    null_ids,
                )

    def cancel_queued_jobs(
        self,
        jobs: Sequence[Job],
        conn: sqlite3.Connection | None = None,
    ) -> None:
        cm = nullcontext(conn) if conn is not None else self.db.connect()

        with cm as conn:
            draft_refs = [
                job.resource
                if isinstance(job, JobDraft) and job.resource is not None else
                None
                for job in jobs
            ]
            resolved_ids = iter(
                self.resolve_refs(
                    [ref for ref in draft_refs if ref is not None],
                    conn=conn,
                )
            )
            targeted: list[tuple[Job, int]] = []
            for job, draft_ref in zip(jobs, draft_refs):
                if draft_ref is None:
                    continue
                targeted.append((job, next(resolved_ids)))
            existing_jobs = self.load_jobs_by_type_and_resource(
                [(job.type, resource_id) for job, resource_id in targeted],
                conn,
            )
            for job, resource_id in targeted:
                existing = existing_jobs.get((job.type, resource_id))
                if existing is None:
                    continue
                job_id, status, priority, parameters = existing
                if status != "queued":
                    continue
                job_class = JobRecord._registry[job.type]
                self.cancel_job(
                    job_class(
                        id=job_id,
                        status=status,
                        priority=priority,
                        resource_id=resource_id,
                        **json.loads(parameters),
                    ),
                    conn=conn,
                )
                existing_jobs[(job.type, resource_id)] = (
                    job_id,
                    "canceled",
                    priority,
                    parameters,
                )

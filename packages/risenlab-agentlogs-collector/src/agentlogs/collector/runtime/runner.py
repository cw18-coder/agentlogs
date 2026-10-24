import datetime as dt
import asyncio
from typing import Any

from .processor import Processor
from .resolver import ResolveJobRecord, Resolver
from ..state import JobRecord, State
from ..api import (
    APIError,
    MaxAttemptsRecoverableError,
    NoAvailableTokenError,
    RateLimitError,
    RecoverableError,
    TokenStore,
)
from ..datetime import get_utc_min, get_utc_now

class Status:
    workers_idle: list[bool]
    idle: bool
    last_seen_queue_generation: int

    running: bool = False
    finished: bool = False

    def __init__(self, n_workers: int):
        self.workers_idle = [False] * n_workers
        self.idle = False
        self.last_seen_queue_generation = -1

    def report_queue_generation(self, queue_generation: int):
        if self.last_seen_queue_generation < queue_generation:
            self.last_seen_queue_generation = queue_generation

    def set_worker_busy(self, worker_index: int):
        self.workers_idle[worker_index] = False
        self.idle = False

    def set_worker_idle(self, worker_index: int):
        self.workers_idle[worker_index] = True
        self.idle = all(self.workers_idle)
    
class PauseController:
    def __init__(self):
        self.resume_datetime = get_utc_min()
        self.lock = asyncio.Lock()

    def is_paused(self) -> bool:
        return self.resume_datetime > get_utc_now()

    async def pause_until(self, datetime: dt.datetime):
        if datetime.tzinfo != dt.timezone.utc:
            raise ValueError("Resume datetime must be in UTC")
        
        async with self.lock:
            self.resume_datetime = max(
                self.resume_datetime,
                datetime,
            )

    async def pause_for(self, duration: dt.timedelta):
        await self.pause_until(get_utc_now() + duration)

    async def wait_if_paused(self):
        while True:
            delay = (self.resume_datetime - get_utc_now()).total_seconds()
            if delay <= 0:
                return
            await asyncio.sleep(delay)


class ProcessorGroup:
    def __init__(
        self,
        processors: list[Processor[Any]],
        share: float = 1.0,
        token_store: TokenStore | None = None,
        wallet: str | None = None,
    ):
        if share <= 0 or share > 1:
            raise ValueError(f"share must be in (0, 1], got {share}")
        types = [
            job_type
            for processor in processors
            for job_type in processor.handled_types()
        ]
        if len(types) != len(set(types)):
            raise ValueError(f"duplicate job types in ProcessorGroup: {types}")
        self.processors = {
            job_type: processor
            for processor in processors
            for job_type in processor.handled_types()
        }
        self.job_types = list(self.processors.keys())
        self.share = share
        self.token_store = token_store
        self.wallet = wallet
        self.pause_controller = PauseController()
        self.busy = 0

    def tokens_available(self) -> bool:
        if self.token_store is None or self.wallet is None:
            return True
        return self.token_store.has_available_token(self.wallet)


class Runner:
    state: State
    processors: dict[str, Processor[Any]]
    job_types: list[str]
    n_workers: int
    description: str
    groups: list[ProcessorGroup]
    group_by_type: dict[str, ProcessorGroup]

    status: Status

    def __init__(
        self,
        state: State,
        processors: list[Processor[Any]] | None = None,
        n_workers: int | None = None,
        description: str = "Runner",
        *,
        groups: list[ProcessorGroup] | None = None,
    ):
        if n_workers is None:
            raise ValueError("n_workers is required")
        if (processors is None) == (groups is None):
            raise ValueError("provide exactly one of processors or groups")
        if groups is None:
            groups = [ProcessorGroup(processors, share=1.0)]
        if not groups:
            raise ValueError("groups must not be empty")

        self.state = state
        self.groups = groups
        self.processors = {}
        self.group_by_type = {}
        for group in groups:
            for job_type, processor in group.processors.items():
                if job_type in self.processors:
                    raise ValueError(f"job type {job_type!r} belongs to more than one ProcessorGroup")
                self.processors[job_type] = processor
                self.group_by_type[job_type] = group
        self.job_types = list(self.processors.keys())
        self.n_workers = n_workers
        self.description = description

        self.status = Status(n_workers)
        self.claim_lock = asyncio.Lock()
        self.attempt_counts: dict[int, int] = {}

    def claim_hierarchy(self) -> list[ProcessorGroup]:
        eligible = [
            group
            for group in self.groups
            if group.job_types
            and not group.pause_controller.is_paused()
            and group.tokens_available()
        ]
        if not eligible:
            return []
        # A paused or tokenless group gives its share to the groups that can run.
        share_total = sum(group.share for group in eligible)
        limits = {
            group: group.share / share_total * self.n_workers
            for group in eligible
        }
        under = [group for group in eligible if group.busy < limits[group]]
        under.sort(key=lambda group: group.busy - limits[group])
        steal = [group for group in eligible if group.busy >= limits[group]]
        return under + steal

    async def wait_if_blocked(self) -> bool:
        # Sleep only for groups that still have queued jobs and cannot run.
        # A group that can run, even with an empty queue, must not park the others.
        resume_at = None
        for group in self.groups:
            if not group.job_types:
                continue
            if self.state.progress.get_job_types_status_counts(group.job_types).queued <= 0:
                continue
            if not group.pause_controller.is_paused() and group.tokens_available():
                return False
            if group.pause_controller.is_paused():
                when = group.pause_controller.resume_datetime
            elif (
                group.token_store is not None
                and group.wallet is not None
                and group.token_store.tokens
            ):
                when = min(
                    group.token_store.token_wallet(token, group.wallet).available_at()
                    for token in group.token_store.tokens
                )
            else:
                continue
            if resume_at is None or when < resume_at:
                resume_at = when
        if resume_at is None:
            return False
        delay = (resume_at - get_utc_now()).total_seconds()
        # Recheck soon. In-flight requests can restore a wallet before reset_at.
        await asyncio.sleep(min(delay, 1) if delay > 0 else 0.05)
        return True

    async def wait_for_work(self, worker_index: int) -> None:
        if await self.wait_if_blocked():
            return
        if any(
            group.job_types
            and self.state.progress.get_job_types_status_counts(group.job_types).queued > 0
            for group in self.groups
        ):
            await asyncio.sleep(1)
            return
        self.status.report_queue_generation(self.state.queue_generation)
        self.status.set_worker_idle(worker_index)
        await asyncio.sleep(1)

    async def process_job(self, job: JobRecord):
        group = self.group_by_type[job.type]
        try:
            try:
                result = await self.processors[job.type].process(job)
                self.state.complete_job(
                    job,
                    jobs=result.jobs if result.jobs is not None else [],
                    resources=result.resources if result.resources is not None else [],
                    cancel_jobs=result.cancel_jobs if result.cancel_jobs is not None else [],
                    continue_job=result.continue_job,
                )
            except ValueError as e:
                self.state.fail_job(
                    job,
                    error=str(e)
                )
                if isinstance(job, ResolveJobRecord):
                    resolver = Resolver.registry[job.resource_type]
                    self.state.cancel_queued_jobs(resolver.cancel_jobs(job.aliases))

        except MaxAttemptsRecoverableError as e:
            attempts = self.attempt_counts.get(job.id, 0) + 1
            self.attempt_counts[job.id] = attempts
            if attempts > e.max_attempts:
                self.state.fail_job(job, error=str(e))
            else:
                self.state.retry_job(job, error=str(e))
                await group.pause_controller.pause_for(dt.timedelta(seconds=1))

        except RecoverableError as e:
            self.state.retry_job(
                job, 
                error=str(e)
            )

            await group.pause_controller.pause_for(dt.timedelta(seconds=1))

        except RateLimitError as e:
            self.state.retry_job(
                job, 
                error=str(e)
            )

        except NoAvailableTokenError as e:
            self.state.retry_job(
                job, 
                error=str(e)
            )

            await group.pause_controller.pause_until(e.reset_time)

        except APIError as e:
            self.state.fail_job(
                job, 
                error=str(e)
            )
    
    async def worker(self, worker_index: int):
        while True:
            async with self.claim_lock:
                ordered = self.claim_hierarchy()
                if not ordered:
                    reserved = None
                    type_groups: list[list[str]] = []
                else:
                    reserved = ordered[0]
                    reserved.busy += 1
                    type_groups = [group.job_types for group in ordered]

            if reserved is None:
                await self.wait_for_work(worker_index)
                continue

            job = self.state.claim_job(type_groups=type_groups)

            if job is None:
                async with self.claim_lock:
                    reserved.busy -= 1
                await self.wait_for_work(worker_index)
                continue

            self.status.report_queue_generation(self.state.queue_generation)

            won = self.group_by_type[job.type]
            if won is not reserved:
                async with self.claim_lock:
                    reserved.busy -= 1
                    won.busy += 1

            try:
                self.status.set_worker_busy(worker_index)
                await self.process_job(job)
            except (Exception, KeyboardInterrupt, asyncio.CancelledError, SystemExit):
                self.state.reset_job(job)
                raise
            finally:
                async with self.claim_lock:
                    won.busy -= 1

    async def run(self):
        if self.status.running:
            raise RuntimeError("Queue already running")
        elif self.status.finished:
            raise RuntimeError("Queue already finished")

        try:
            async with asyncio.TaskGroup() as task_group:
                for i in range(self.n_workers):
                    task_group.create_task(self.worker(i))
                
            self.status.finished = True

        finally:
            self.status.running = False

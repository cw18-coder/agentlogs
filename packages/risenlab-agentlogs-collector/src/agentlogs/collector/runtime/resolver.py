from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any, ClassVar

from ..api import NotFoundError
from ..api.graphql import GraphQLAPI
from ..api.rest import RestAPI
from ..state import State
from ..state.job import Job, JobDraft, JobRecord
from ..state.resource import ResourceRef
from .processor import Processor, Result


@dataclass
class ResolveJob(Job):
    resource_type: str
    resolve_using: str
    aliases: dict[str, str]

    @property
    def type(self) -> str:
        return f"collect_{self.resource_type}_{self.resolve_using}"


@dataclass
class ResolveJobDraft(ResolveJob, JobDraft):
    requeue: ClassVar[bool] = False


@dataclass
class ResolveJobRecord(ResolveJob, JobRecord, register=False):
    pass


@dataclass(frozen=True)
class Step:
    resolve_using: str
    required_aliases: tuple[str, ...]
    priority: int
    fetch: Callable[[Any, dict[str, str]], Awaitable[dict[str, Any]]]


class Resolver(ABC):
    registry: ClassVar[dict[str, type[Resolver]]] = {}

    resource_type: ClassVar[str]
    graphql: ClassVar[tuple[Step, ...]]
    rest: ClassVar[tuple[Step, ...]]

    def __init_subclass__(cls, **kwargs: Any):
        super().__init_subclass__(**kwargs)
        resource_type = cls.__dict__.get("resource_type")
        if resource_type is None:
            return
        Resolver.registry[resource_type] = cls
        for step in (*cls.graphql, *cls.rest):
            job_type = f"collect_{resource_type}_{step.resolve_using}"
            if job_type in JobRecord._registry:
                raise ValueError(f"Duplicate job type: {job_type}")
            JobRecord._registry[job_type] = ResolveJobRecord

    @classmethod
    def collect_job_type(cls, resolve_using: str) -> str:
        return f"collect_{cls.resource_type}_{resolve_using}"

    @classmethod
    def job_types_for_api(cls, api: str) -> list[str]:
        job_types: list[str] = []
        for resolver in cls.registry.values():
            wallet_steps = resolver.graphql if api == "graphql" else resolver.rest
            job_types.extend(
                resolver.collect_job_type(step.resolve_using)
                for step in wallet_steps
            )
        return job_types

    @classmethod
    def step_for(cls, resolve_using: str) -> Step:
        for step in (*cls.graphql, *cls.rest):
            if step.resolve_using == resolve_using:
                return step
        raise ValueError(
            f"unknown resolve_using {resolve_using!r} for {cls.resource_type}"
        )

    @classmethod
    def step_is_eligible(
        cls,
        step: Step,
        aliases: dict[str, str],
        tried: set[str],
    ) -> bool:
        if step.resolve_using in tried:
            return False
        return all(
            aliases.get(alias_key) not in (None, "")
            for alias_key in step.required_aliases
        )

    @classmethod
    def aliases_from(cls, resource: ResourceRef | dict[str, str]) -> dict[str, str]:
        if isinstance(resource, dict):
            raw = resource
        else:
            raw = {alias.key: alias.value for alias in resource.aliases}
        fields: dict[str, str] = {}
        for alias_key, alias_value in raw.items():
            if alias_value in (None, ""):
                continue
            parts = alias_key.split(":")
            values = str(alias_value).split(":", len(parts) - 1)
            if len(parts) == 1 or len(values) != len(parts):
                fields[alias_key] = str(alias_value)
                continue
            for part, value in zip(parts, values, strict=True):
                fields[part] = value
        return fields

    @classmethod
    def draft_for(cls, step: Step, aliases: dict[str, str]) -> ResolveJobDraft:
        present_aliases = cls.aliases_from(aliases)
        resource_ref_class = ResourceRef._registry[cls.resource_type]
        return ResolveJobDraft(
            resource_type=cls.resource_type,
            resolve_using=step.resolve_using,
            aliases=present_aliases,
            resource=resource_ref_class(**present_aliases),
            priority=step.priority,
        )

    @classmethod
    def alias_groups(
        cls,
        resource: ResourceRef | dict[str, str] | Sequence[ResourceRef | dict[str, str]],
    ) -> list[dict[str, str]]:
        if isinstance(resource, Sequence) and not isinstance(resource, str):
            items = list(resource)
        else:
            items = [resource]
        parent = list(range(len(items)))

        def find(index: int) -> int:
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        seen: dict[tuple[str, str], int] = {}
        fields_by_item: list[dict[str, str]] = []
        for index, item in enumerate(items):
            if isinstance(item, dict):
                pairs = {
                    (key, value)
                    for key, value in item.items()
                    if value not in (None, "")
                }
            else:
                pairs = {(alias.key, alias.value) for alias in item.aliases}
            fields_by_item.append(cls.aliases_from(item))
            for pair in pairs:
                other = seen.get(pair)
                if other is None:
                    seen[pair] = index
                else:
                    parent[find(index)] = find(other)
        groups: dict[int, dict[str, str]] = {}
        for index, fields in enumerate(fields_by_item):
            groups.setdefault(find(index), {}).update(fields)
        return list(groups.values())

    @classmethod
    def next_jobs(
        cls,
        resource: ResourceRef | dict[str, str] | Sequence[ResourceRef | dict[str, str]],
        tried: set[str] | None = None,
    ) -> list[JobDraft]:
        tried_resolve_using = tried if tried is not None else set()
        jobs: list[JobDraft] = []
        for aliases in cls.alias_groups(resource):
            for wallet_steps in (cls.graphql, cls.rest):
                for step in wallet_steps:
                    if cls.step_is_eligible(step, aliases, tried_resolve_using):
                        jobs.append(cls.draft_for(step, aliases))
                        break
        return jobs

    @classmethod
    def cancel_jobs(cls, resource: ResourceRef | dict[str, str]) -> list[JobDraft]:
        aliases = cls.aliases_from(resource)
        return [
            cls.draft_for(step, aliases)
            for step in (*cls.graphql, *cls.rest)
        ]

    @classmethod
    def obsolete_jobs(
        cls,
        resource: ResourceRef | dict[str, str] | Sequence[ResourceRef | dict[str, str]],
    ) -> list[JobDraft]:
        jobs: list[JobDraft] = []
        for aliases in cls.alias_groups(resource):
            for wallet_steps in (cls.graphql, cls.rest):
                kept_preferred_step = False
                for step in wallet_steps:
                    if not cls.step_is_eligible(step, aliases, set()):
                        continue
                    if not kept_preferred_step:
                        kept_preferred_step = True
                        continue
                    jobs.append(cls.draft_for(step, aliases))
        return jobs

    @classmethod
    @abstractmethod
    def resolved(cls, body: dict[str, Any], job: ResolveJob) -> Result:
        ...

    @classmethod
    def unfound(cls, job: ResolveJob) -> Result:
        return Result()


async def run_resolver(state: State, api: Any, job: ResolveJobRecord) -> Result:
    resolver = Resolver.registry[job.resource_type]
    step = resolver.step_for(job.resolve_using)
    try:
        body = await step.fetch(api, job.aliases)
    except NotFoundError:
        if (
            job.resource_id is not None
            and state.payload_storage.load_payload(job.resource_type, job.resource_id)
            is not None
        ):
            return Result()
        tried = {job.resolve_using}
        if job.resource_id is not None:
            prefix = f"collect_{job.resource_type}_"
            with state.db.connect() as conn:
                existing = state.load_jobs_by_type_and_resource(
                    [
                        (resolver.collect_job_type(candidate.resolve_using), job.resource_id)
                        for candidate in (*resolver.graphql, *resolver.rest)
                    ],
                    conn,
                )
            for (job_type, _), (_, status, _, _) in existing.items():
                if status == "completed" and job_type.startswith(prefix):
                    tried.add(job_type.removeprefix(prefix))
        jobs = resolver.next_jobs(job.aliases, tried=tried)
        if jobs:
            return Result(jobs=jobs)
        return resolver.unfound(job)
    result = resolver.resolved(body, job)
    aliases = dict(job.aliases)
    if result.resources:
        for resource in result.resources:
            if resource.type == resolver.resource_type:
                for alias in resource.aliases:
                    aliases[alias.key] = alias.value
    return Result(
        jobs=result.jobs,
        resources=result.resources,
        cancel_jobs=list(result.cancel_jobs or []) + resolver.cancel_jobs(aliases),
    )


class ResolveGraphql(Processor[ResolveJobRecord]):
    job_class = ResolveJobRecord

    def __init__(self, api: GraphQLAPI, state: State):
        self.api = api
        self.state = state

    def handled_types(self) -> list[str]:
        return Resolver.job_types_for_api("graphql")

    async def run(self, job: ResolveJobRecord) -> Result:
        return await run_resolver(self.state, self.api, job)


class ResolveRest(Processor[ResolveJobRecord]):
    job_class = ResolveJobRecord

    def __init__(self, api: RestAPI, state: State):
        self.api = api
        self.state = state

    def handled_types(self) -> list[str]:
        return Resolver.job_types_for_api("rest")

    async def run(self, job: ResolveJobRecord) -> Result:
        return await run_resolver(self.state, self.api, job)

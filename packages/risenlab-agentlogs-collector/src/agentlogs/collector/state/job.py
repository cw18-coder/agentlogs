from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any, ClassVar, Literal

from .resource import ResourceRef


type JobStatus = Literal["queued", "running", "completed", "failed", "canceled"]


@dataclass
class Job:
    type: ClassVar[str]

    priority: int = field(default=1, kw_only=True)

    def get_parameters(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in asdict(self).items()
            if key not in (
                "priority",
                "type",
                "requeue",
                "id",
                "status",
                "error",
                "resource",
                "resource_id",
            )
        }


@dataclass
class JobDraft(Job):
    requeue: ClassVar[bool] = True
    resource: ResourceRef | None = field(default=None, kw_only=True)


@dataclass
class JobRecord(Job):
    _registry: ClassVar[dict[str, type[JobRecord]]] = {}

    id: int = field(kw_only=True)
    status: JobStatus = field(kw_only=True)
    error: str | None = field(default=None, kw_only=True)
    resource_id: int | None = field(default=None, kw_only=True)

    def __init_subclass__(cls, register: bool = True, **kwargs: Any):
        super().__init_subclass__(**kwargs)
        if not register:
            return
        if cls.type in JobRecord._registry:
            raise ValueError(f"Duplicate job type: {cls.type}")

        JobRecord._registry[cls.type] = cls

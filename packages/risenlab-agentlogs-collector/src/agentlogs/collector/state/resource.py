from __future__ import annotations
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, ClassVar


@dataclass(frozen=True)
class Alias:
    key: str
    value: str

    def __post_init__(self):
        if self.key in {"login", "full_name"} or self.key.startswith("repository_name"):
            object.__setattr__(self, "value", self.value.lower())


@dataclass
class ResourceRef:
    type: ClassVar[str]
    alias_hierarchy: ClassVar[list[str]]
    _registry: ClassVar[dict[str, type[ResourceRef]]] = {}

    def __init_subclass__(cls):
        type_name = cls.__dict__.get("type")
        if type_name is None:
            return
        alias_keys = cls.__dict__.get("alias_hierarchy")
        if alias_keys is None:
            raise ValueError(f"{cls.__name__} must define alias_hierarchy")
        if len(set(alias_keys)) != len(alias_keys):
            raise ValueError(f"Duplicate alias key on resource type {type_name!r}")
        for key in alias_keys:
            parts = key.split(":")
            if any(part == "" for part in parts):
                raise ValueError(f"Invalid alias key {key!r} on resource type {type_name!r}")
        if type_name in ResourceRef._registry:
            raise ValueError(f"Duplicate resource type: {type_name}")
        ResourceRef._registry[type_name] = cls

    def __post_init__(self):
        for field_name in {
            part
            for key in self.alias_hierarchy
            for part in key.split(":")
        }:
            value = getattr(self, field_name, None)
            if value is not None:
                setattr(self, field_name, str(value))
        login = getattr(self, "login", None)
        if login is not None:
            self.login = login.lower()
        repository_name = getattr(self, "repository_name", None)
        if repository_name is not None:
            self.repository_name = repository_name.lower()
        full_name = getattr(self, "full_name", None)
        if full_name is not None:
            self.full_name = full_name.lower()
        if not self.aliases:
            raise ValueError(f"{type(self).__name__} must have at least one alias")

    @property
    def aliases(self) -> list[Alias]:
        aliases: list[Alias] = []
        for key in self.alias_hierarchy:
            parts = key.split(":")
            values = [getattr(self, part, None) for part in parts]
            if any(value is None for value in values):
                continue
            aliases.append(Alias(key=key, value=":".join(str(value) for value in values)))
        return aliases

    @property
    def alias(self) -> Alias:
        return self.aliases[0]

    @classmethod
    def from_aliases(cls, type_name: str, aliases: Sequence[Alias]) -> ResourceRef:
        try:
            ref_class = ResourceRef._registry[type_name]
        except KeyError:
            raise ValueError(f"Unknown resource type: {type_name!r}") from None
        fields: dict[str, str] = {}
        for alias in aliases:
            parts = alias.key.split(":")
            values = alias.value.split(":", len(parts) - 1)
            if len(values) != len(parts):
                raise ValueError(
                    f"Alias {alias.key}={alias.value!r} does not match key parts"
                )
            for part, value in zip(parts, values, strict=True):
                fields[part] = value
        return ref_class(**fields)


@dataclass
class Resource:
    metadata: dict[str, str | None] = field(default_factory=dict)
    relations_from: dict[str, list[ResourceRef]] = field(default_factory=dict)
    relations_to: dict[str, list[ResourceRef]] = field(default_factory=dict)
    found: bool | None = None


@dataclass
class ResourceDraft(Resource):
    payload: Any | None = None


@dataclass
class ResourceRecord(Resource):
    id: int = field(kw_only=True)
    type: str = field(kw_only=True)
    aliases: dict[str, str] = field(kw_only=True)
    payload_loader: Callable[[], Any] | None = field(default=None, repr=False)
    loaded_payload: Any | None = field(default=None, init=False, repr=False)
    payload_is_loaded: bool = field(default=False, init=False, repr=False)

    def __post_init__(self):
        if not self.aliases:
            raise ValueError(f"Resource {self.id} has no aliases")

    @property
    def alias(self) -> Alias:
        key, value = next(iter(self.aliases.items()))
        return Alias(key=key, value=value)

    @property
    def payload(self) -> Any | None:
        if not self.payload_is_loaded:
            if self.payload_loader is not None:
                self.loaded_payload = self.payload_loader()
            else:
                self.loaded_payload = None
            self.payload_is_loaded = True
        return self.loaded_payload

    def release_payload(self) -> None:
        self.loaded_payload = None
        self.payload_is_loaded = False

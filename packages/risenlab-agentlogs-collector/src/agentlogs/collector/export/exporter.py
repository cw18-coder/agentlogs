from abc import ABC, abstractmethod
import gc
from os import PathLike
from pathlib import Path
from typing import Any, ClassVar, Generic, Mapping, TypeVar

import pyarrow as pa
import pyarrow.parquet as pq
from tqdm.auto import tqdm

from .arrow import arrow_schema_from_typed_dict
from ..state import State, ResourceRecord

T = TypeVar("T", bound=Mapping[str, Any])
class Exporter(ABC, Generic[T]):
    resource_type: ClassVar[str]
    expand_relations: ClassVar[list[str]] = []
    load_relations_for: ClassVar[list[str]] = []

    state: State
    path: Path
    schema: pa.Schema

    def __init__(self, state: State, path: str | PathLike[str]):
        self.state = state
        self.path = Path(path)
        self.schema = arrow_schema_from_typed_dict(self.get_record_type())

    @abstractmethod
    def get_record_type(self) -> type[T]:
        pass

    def prepare_page(self, resources: list[ResourceRecord]) -> None:
        return

    @abstractmethod
    def format_resource(
        self, 
        resource: ResourceRecord, 
        expanded_resources_from: dict[str, list[ResourceRecord]],
        expanded_resources_to: dict[str, list[ResourceRecord]]
    ) -> T | list[T] | None:
        pass

    def export(
        self,
        shard_size: int = 100_000,
        batch_size: int = 25_000,
    ) -> None:
        if shard_size < 1 or batch_size < 1:
            raise ValueError("shard_size and batch_size must be at least 1")
        if batch_size > shard_size:
            raise ValueError("batch_size must be at most shard_size")

        if self.path.exists():
            raise ValueError(f"Path {self.path} already exists")

        self.path.mkdir(parents=True)

        resource_count = self.state.count_resources([self.resource_type])
        progress = tqdm(
            total=resource_count,
            desc=f"Exporting {self.resource_type}",
            position=0,
            leave=True,
        )
        after_id = 0
        shard_index = 0
        shard_rows = 0
        pending: list[T] = []
        writer: pq.ParquetWriter | None = None
        part_paths: list[Path] = []

        def write_chunk(rows: list[T]) -> None:
            nonlocal shard_rows, writer
            table = self.table_from_rows(rows)
            if writer is None:
                path = self.path / f"part_{shard_index:05}.parquet"
                part_paths.append(path)
                writer = pq.ParquetWriter(path, self.schema, write_page_index=False)
            writer.write_table(table, row_group_size=table.num_rows)
            shard_rows += table.num_rows
            del table
            gc.collect()
            pa.default_memory_pool().release_unused()

        def seal_shard() -> None:
            nonlocal shard_index, shard_rows, writer
            if writer is None:
                return
            writer.close()
            writer = None
            shard_index += 1
            shard_rows = 0

        def add_rows(rows: list[T]) -> None:
            pending.extend(rows)
            while pending:
                room = shard_size - shard_rows
                if len(pending) < min(batch_size, room):
                    return
                take = min(batch_size, room)
                write_chunk(pending[:take])
                del pending[:take]
                if shard_rows >= shard_size:
                    seal_shard()

        def close_shard() -> None:
            if pending:
                write_chunk(pending)
                pending.clear()
            seal_shard()

        try:
            while True:
                resources = self.state.load_resources(
                    self.resource_type,
                    limit=20_000,
                    after_id=after_id,
                )
                if not resources:
                    break
                after_id = resources[-1].id
                self.prepare_page(resources)
                related_refs = [
                    related_resource_ref
                    for resource in resources
                    for relation_type in self.expand_relations
                    for related_resource_ref in (
                        resource.relations_from.get(relation_type, [])
                        + resource.relations_to.get(relation_type, [])
                    )
                ]
                related_refs_with_relations = []
                related_refs_without_relations = []
                for related_resource_ref in related_refs:
                    if related_resource_ref.type in self.load_relations_for:
                        related_refs_with_relations.append(related_resource_ref)
                    else:
                        related_refs_without_relations.append(related_resource_ref)
                related_resources: dict[tuple[str, str, str], ResourceRecord] = {}
                for record in (
                    self.state.load_resources_from_refs(related_refs_with_relations)
                    + self.state.load_resources_from_refs(
                        related_refs_without_relations,
                        load_relations=False,
                    )
                ):
                    for key, value in record.aliases.items():
                        related_resources[(record.type, key, value)] = record

                for resource in resources:
                    try:
                        formatted_resource = self.format_resource(
                            resource,
                            expanded_resources_from={
                                relation_type: [
                                    related_resources[
                                        (
                                            related_resource_ref.type,
                                            related_resource_ref.alias.key,
                                            related_resource_ref.alias.value,
                                        )
                                    ]
                                    for related_resource_ref in resource.relations_from.get(relation_type, [])
                                ]
                                for relation_type in self.expand_relations
                            },
                            expanded_resources_to={
                                relation_type: [
                                    related_resources[
                                        (
                                            related_resource_ref.type,
                                            related_resource_ref.alias.key,
                                            related_resource_ref.alias.value,
                                        )
                                    ]
                                    for related_resource_ref in resource.relations_to.get(relation_type, [])
                                ]
                                for relation_type in self.expand_relations
                            },
                        )
                    except Exception as e:
                        alias_text = ", ".join(
                            f"{key}={value!r}" for key, value in resource.aliases.items()
                        )
                        raise ValueError(
                            f"Error formatting {resource.type} '{alias_text}'"
                        ) from e
                    if resource.payload_is_loaded:
                        resource.release_payload()
                    if isinstance(formatted_resource, list):
                        add_rows(formatted_resource)
                    elif formatted_resource is not None:
                        add_rows([formatted_resource])
                    del formatted_resource
                    progress.update(1)

                del resources
                del related_resources

            close_shard()
            n_shards = len(part_paths)
            for index, path in enumerate(part_paths):
                path.rename(self.path / f"part_{index:05}_of_{n_shards:05}.parquet")
        finally:
            if writer is not None:
                writer.close()
            progress.close()

    def table_from_rows(self, rows: list[T]) -> pa.Table:
        try:
            return pa.Table.from_pylist(rows, schema=self.schema)
        except UnicodeEncodeError:
            return pa.Table.from_pylist(
                [sanitize_utf8(row) for row in rows],
                schema=self.schema,
            )

def fix_surrogates(value: str) -> str:
    if not any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        return value
    parts: list[str] = []
    index = 0
    while index < len(value):
        hi = ord(value[index])
        lo = ord(value[index + 1]) if index + 1 < len(value) else 0
        if 0xD800 <= hi <= 0xDBFF and 0xDC00 <= lo <= 0xDFFF:
            parts.append(chr(0x10000 + ((hi - 0xD800) << 10) + (lo - 0xDC00)))
            index += 2
        else:
            parts.append(value[index])
            index += 1
    return "".join(parts).encode("utf-16", "surrogatepass").decode("utf-16", "replace")


def sanitize_utf8(value: Any) -> Any:
    if isinstance(value, str):
        return fix_surrogates(value)
    if isinstance(value, list):
        return [sanitize_utf8(item) for item in value]
    if isinstance(value, dict):
        return {key: sanitize_utf8(item) for key, item in value.items()}
    
    return value
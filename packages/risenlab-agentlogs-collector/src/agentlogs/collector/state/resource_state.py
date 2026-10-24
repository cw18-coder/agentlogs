from contextlib import nullcontext
import logging
import sqlite3
from typing import Any, Sequence

from .progress import Progress
from .resource import Alias, ResourceDraft, ResourceRecord, ResourceRef
from .storage import Database, PayloadStorage

SQLITE_VAR_LIMIT = 200000

logger = logging.getLogger(__name__)


class ResourceState:
    db: Database
    payload_storage: PayloadStorage
    progress: Progress

    def get_resource_type(self, type_name: str) -> type[ResourceRef]:
        try:
            return ResourceRef._registry[type_name]
        except KeyError:
            raise ValueError(f"Unknown resource type: {type_name!r}") from None

    def require_known_aliases(
        self,
        type_name: str,
        aliases: Sequence[Alias],
    ) -> list[str]:
        allowed = self.get_resource_type(type_name).alias_hierarchy
        unspecified = [alias.key for alias in aliases if alias.key not in allowed]
        if unspecified:
            raise ValueError(
                f"Unspecified alias key={unspecified[0]!r} for resource type={type_name!r}; "
                f"allowed={allowed}"
            )
        return allowed

    def save_resources(
        self,
        resources: Sequence[ResourceDraft],
        conn: sqlite3.Connection | None = None,
    ) -> None:
        cm = nullcontext(conn) if conn is not None else self.db.connect()

        with cm as conn:
            kept: list[tuple[ResourceDraft, int]] = []
            for resource in resources:
                if not resource.aliases:
                    raise ValueError(f"Resource has no aliases: type={resource.type!r}")
            created_ids: set[int] = set()
            alias_hits = {
                (resource_type, key, value): resource_id
                for resource_id, resource_type, key, value in self.get_aliases_by_keys(
                    [
                        (resource.type, alias.key, alias.value)
                        for resource in resources
                        for alias in resource.aliases
                    ],
                    conn=conn,
                )
            }

            for resource in resources:
                resolved = self.resolve_resource(resource, alias_hits, conn=conn)
                if resolved is None:
                    continue
                resource_id, created = resolved
                kept.append((resource, resource_id))
                if created:
                    created_ids.add(resource_id)

            directed: list[tuple[int, ResourceRef, str, bool]] = []
            for resource, resource_id in kept:
                directed.extend(
                    (resource_id, related_ref, relation_type, True)
                    for relation_type, related_refs in (resource.relations_from or {}).items()
                    for related_ref in related_refs
                )
                directed.extend(
                    (resource_id, related_ref, relation_type, False)
                    for relation_type, related_refs in (resource.relations_to or {}).items()
                    for related_ref in related_refs
                )
            related_ids = self.resolve_refs(
                [related_ref for _, related_ref, _, _ in directed],
                conn=conn,
            )
            relation_triples: list[tuple[int, int, str]] = []
            for (self_id, _, relation_type, is_from), related_id in zip(directed, related_ids):
                if is_from:
                    relation_triples.append((self_id, related_id, relation_type))
                else:
                    relation_triples.append((related_id, self_id, relation_type))

            self.create_update_resource_relations(relation_triples, conn=conn)

            self.create_update_resource_metadata(
                [
                    (resource_id, key, value)
                    for resource, resource_id in kept
                    for key, value in (resource.metadata or {}).items()
                ],
                conn=conn,
            )

            self.save_resources_payloads(
                [
                    (resource.type, resource_id, resource.payload)
                    for resource, resource_id in kept
                    if resource.payload is not None
                ],
                conn=conn,
            )
            for resource, resource_id in kept:
                if resource.found is False:
                    self.set_resource_found_false(resource.type, resource_id, conn)

    def resolve_resource(
        self,
        resource: ResourceDraft,
        alias_hits: dict[tuple[str, str, str], int],
        conn: sqlite3.Connection | None = None,
    ) -> tuple[int, bool] | None:
        if len({alias.key for alias in resource.aliases}) != len(resource.aliases):
            raise ValueError(
                f"Resource aliases contradict: incoming type={resource.type!r} "
                f"aliases=[{', '.join(f'{alias.key}={alias.value!r}' for alias in resource.aliases)}]"
            )
        self.require_known_aliases(resource.type, resource.aliases)

        cm = nullcontext(conn) if conn is not None else self.db.connect()

        with cm as conn:
            found_ids = {
                alias_hits[(resource.type, alias.key, alias.value)]
                for alias in resource.aliases
                if (resource.type, alias.key, alias.value) in alias_hits
            }

            if len(found_ids) > 1:
                previous_ids = set(found_ids)
                merged_id = self.merge_resources(resource, found_ids, conn=conn)
                if merged_id is None:
                    return None
                for key, hit_id in list(alias_hits.items()):
                    if hit_id in previous_ids:
                        alias_hits[key] = merged_id
                found_ids = {merged_id}

            if len(found_ids) == 1:
                resource_id = next(iter(found_ids))
                stored = self.get_resource_aliases_and_types([resource_id], conn=conn)[0][resource_id]
                stored_by_key = {alias.key: alias.value for alias in stored}
                conflicting = [
                    alias
                    for alias in resource.aliases
                    if (
                        alias.key in stored_by_key
                        and stored_by_key[alias.key] != alias.value
                    )
                ]
                if conflicting:
                    raise ValueError(
                        self.alias_conflict_message(
                            "Resource aliases contradict existing row",
                            resource.type,
                            resource.aliases,
                            [resource_id],
                            conn=conn,
                        )
                    )

                new_aliases = [
                    alias for alias in resource.aliases if alias.key not in stored_by_key
                ]
                if new_aliases:
                    conn.execute(
"""
UPDATE Resource SET updated_at = CURRENT_TIMESTAMP WHERE id = :id
""",
                        {"id": resource_id},
                    )
                    conn.executemany(
"""
INSERT INTO ResourceAlias (resource_id, type, key, value, created_at, updated_at)
VALUES (:resource_id, :type, :key, :value, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
""",
                        [
                            {
                                "resource_id": resource_id,
                                "type": resource.type,
                                "key": alias.key,
                                "value": alias.value,
                            }
                            for alias in new_aliases
                        ],
                    )
                    for alias in new_aliases:
                        alias_hits[(resource.type, alias.key, alias.value)] = resource_id
                return resource_id, False

            resource_id = conn.execute(
"""
INSERT INTO Resource (type, created_at, updated_at)
VALUES (:type, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
""",
                {"type": resource.type},
            ).lastrowid
            if resource_id is None:
                raise RuntimeError("INSERT Resource did not return an id")
            conn.executemany(
"""
INSERT INTO ResourceAlias (resource_id, type, key, value, created_at, updated_at)
VALUES (:resource_id, :type, :key, :value, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
""",
                [
                    {
                        "resource_id": resource_id,
                        "type": resource.type,
                        "key": alias.key,
                        "value": alias.value,
                    }
                    for alias in resource.aliases
                ],
            )
            self.progress.mutate_resource_create(resource.type)
            for alias in resource.aliases:
                alias_hits[(resource.type, alias.key, alias.value)] = resource_id
            return resource_id, True

    def merge_resources(
        self,
        resource: ResourceDraft,
        found_ids: set[int],
        conn: sqlite3.Connection | None = None,
    ) -> int | None:
        cm = nullcontext(conn) if conn is not None else self.db.connect()

        with cm as conn:
            existing, _ = self.get_resource_aliases_and_types(sorted(found_ids), conn=conn)
            key_values: dict[str, str] = {}
            for resource_id in found_ids:
                for alias in existing[resource_id]:
                    if alias.key in key_values and key_values[alias.key] != alias.value:
                        logger.warning(
                            self.alias_conflict_message(
                                "Resource aliases contradict; not merging",
                                resource.type,
                                resource.aliases,
                                found_ids,
                                conn=conn,
                            )
                        )
                        return None
                    key_values[alias.key] = alias.value
            for alias in resource.aliases:
                if alias.key in key_values and key_values[alias.key] != alias.value:
                    logger.warning(
                        self.alias_conflict_message(
                            "Resource aliases contradict; not merging",
                            resource.type,
                            resource.aliases,
                            found_ids,
                            conn=conn,
                        )
                    )
                    return None

            key_index = {
                key: i for i, key in enumerate(self.get_resource_type(resource.type).alias_hierarchy)
            }
            rank_of = {
                resource_id: min(key_index[alias.key] for alias in existing[resource_id])
                for resource_id in found_ids
            }
            if len(set(rank_of.values())) != len(rank_of):
                raise ValueError(
                    self.alias_conflict_message(
                        "Resource alias ranks tied",
                        resource.type,
                        resource.aliases,
                        found_ids,
                        conn=conn,
                    )
                )
            ordered_ids = sorted(found_ids, key=lambda resource_id: rank_of[resource_id])
            winner_id = ordered_ids[0]
            chosen_payload = None
            for resource_id in ordered_ids:
                loaded = self.payload_storage.load_payload(resource.type, resource_id)
                if loaded is not None:
                    chosen_payload = loaded
                    break

            created_at, = conn.execute(
f"""
SELECT MIN(created_at) FROM Resource
WHERE id IN ({",".join("?" * len(found_ids))})
""",
                list(found_ids),
            ).fetchone()

            loser_ids = ordered_ids[1:]
            loser_set = set(loser_ids)
            loser_placeholders = ",".join("?" * len(loser_ids))
            self.remap_resource_jobs(loser_ids, winner_id, conn=conn)

            seen_relations: set[tuple[str, int, int]] = set()
            relation_rows: list[tuple[str, int, int]] = []
            for column in ("from_resource_id", "to_resource_id"):
                for relation_type, from_id, to_id in conn.execute(
f"""
SELECT type, from_resource_id, to_resource_id FROM ResourceRelation
WHERE {column} IN ({loser_placeholders})
""",
                    loser_ids,
                ).fetchall():
                    row_key = (relation_type, from_id, to_id)
                    if row_key in seen_relations:
                        continue
                    seen_relations.add(row_key)
                    relation_rows.append((relation_type, from_id, to_id))
            self.create_update_resource_relations(
                [
                    (new_from, new_to, relation_type)
                    for relation_type, from_id, to_id in relation_rows
                    if (
                        (new_from := winner_id if from_id in loser_set else from_id)
                        != (new_to := winner_id if to_id in loser_set else to_id)
                    )
                ],
                conn=conn,
            )
            for column in ("from_resource_id", "to_resource_id"):
                conn.execute(
f"""
DELETE FROM ResourceRelation
WHERE {column} IN ({loser_placeholders})
""",
                    loser_ids,
                )

            found_by_id = {
                resource_id: found
                for resource_id, found in conn.execute(
f"""
SELECT id, found FROM Resource
WHERE id IN ({",".join("?" * (len(loser_ids) + 1))})
""",
                    [winner_id, *loser_ids],
                )
            }
            conn.execute(
f"""
INSERT INTO ResourceMetadata (resource_id, key, value, created_at, updated_at)
SELECT ?, key, value, created_at, CURRENT_TIMESTAMP
FROM ResourceMetadata
WHERE resource_id IN ({loser_placeholders})
ORDER BY CASE resource_id {" ".join(f"WHEN ? THEN {index}" for index in range(len(loser_ids)))} END
ON CONFLICT(resource_id, key) DO NOTHING
""",
                [winner_id, *loser_ids, *loser_ids],
            )
            conn.execute(
f"""
DELETE FROM ResourceMetadata WHERE resource_id IN ({loser_placeholders})
""",
                loser_ids,
            )

            conn.execute(
f"""
UPDATE ResourceAlias
SET resource_id = ?, updated_at = CURRENT_TIMESTAMP
WHERE resource_id IN ({loser_placeholders})
""",
                [winner_id, *loser_ids],
            )

            conn.execute(
f"""
DELETE FROM Resource WHERE id IN ({loser_placeholders})
""",
                loser_ids,
            )
            self.progress.mutate_resource_delete(resource.type, len(loser_ids))
            for resource_id in loser_ids:
                found = found_by_id.get(resource_id)
                if found == 0:
                    self.progress.mutate_resource_not_found_delete(resource.type)
                elif found == 1:
                    self.progress.mutate_resource_found_delete(resource.type)

            if chosen_payload is not None:
                self.payload_storage.save_payload(resource.type, winner_id, chosen_payload)
                self.set_resource_found_true(resource.type, winner_id, conn)
            elif found_by_id.get(winner_id) is None and any(
                found_by_id.get(resource_id) == 0 for resource_id in loser_ids
            ):
                self.set_resource_found_false(resource.type, winner_id, conn)

            conn.execute(
"""
UPDATE Resource
SET created_at = :created_at, updated_at = CURRENT_TIMESTAMP
WHERE id = :id
""",
                {"id": winner_id, "created_at": created_at},
            )
            return winner_id

    def resolve_ref(
        self,
        ref: ResourceRef,
        conn: sqlite3.Connection | None = None,
    ) -> int:
        return self.resolve_refs([ref], conn=conn)[0]

    def resolve_refs(
        self,
        refs: Sequence[ResourceRef],
        conn: sqlite3.Connection | None = None,
    ) -> list[int]:
        if not refs:
            return []

        for ref in refs:
            self.require_known_aliases(ref.type, ref.aliases)

        cm = nullcontext(conn) if conn is not None else self.db.connect()

        with cm as conn:
            hits = {
                (resource_type, key, value): resource_id
                for resource_id, resource_type, key, value in self.get_aliases_by_keys(
                    [
                        (ref.type, alias.key, alias.value)
                        for ref in refs
                        for alias in ref.aliases
                    ],
                    conn=conn,
                )
            }
            resource_ids: list[int] = []
            for ref in refs:
                found_ids = {
                    hits[(ref.type, alias.key, alias.value)]
                    for alias in ref.aliases
                    if (ref.type, alias.key, alias.value) in hits
                }
                if len(found_ids) > 1:
                    raise ValueError(
                        self.alias_conflict_message(
                            "Resource aliases hit multiple rows",
                            ref.type,
                            ref.aliases,
                            found_ids,
                            conn=conn,
                        )
                    )
                if len(found_ids) != 1:
                    incoming_text = ", ".join(
                        f"{alias.key}={alias.value!r}" for alias in ref.aliases
                    )
                    raise ValueError(
                        f"Related resource not found: type={ref.type!r} "
                        f"aliases=[{incoming_text}]"
                    )
                resource_ids.append(next(iter(found_ids)))
            return resource_ids

    def alias_conflict_message(
        self,
        reason: str,
        incoming_type: str,
        incoming_aliases: Sequence[Alias],
        resource_ids: Sequence[int],
        conn: sqlite3.Connection | None = None,
    ) -> str:
        incoming_text = ", ".join(
            f"{alias.key}={alias.value!r}" for alias in incoming_aliases
        )
        existing, _ = self.get_resource_aliases_and_types(sorted(resource_ids), conn=conn)
        existing_text = "; ".join(
            "id="
            + str(resource_id)
            + " aliases=["
            + ", ".join(
                f"{alias.key}={alias.value!r}"
                for alias in existing[resource_id]
            )
            + "]"
            for resource_id in sorted(resource_ids)
        )
        return (
            f"{reason}: incoming type={incoming_type!r} "
            f"aliases=[{incoming_text}]; existing {existing_text}"
        )

    def create_update_resource_relations(
        self,
        relations: Sequence[tuple[int, int, str]],
        conn: sqlite3.Connection | None = None,
    ) -> None:
        cm = nullcontext(conn) if conn is not None else self.db.connect()

        with cm as conn:
            conn.executemany(
"""
INSERT INTO ResourceRelation (type, from_resource_id, to_resource_id, created_at, updated_at)
VALUES (:type, :from_id, :to_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT(type, from_resource_id, to_resource_id) DO UPDATE SET updated_at = CURRENT_TIMESTAMP;
""",
                [
                    {
                        "type": relation_type,
                        "from_id": from_resource_id,
                        "to_id": to_resource_id,
                    } for from_resource_id, to_resource_id, relation_type in relations
                ]
            )

    def create_update_resource_metadata(
        self,
        metadata: Sequence[tuple[int, str, str | None]],
        conn: sqlite3.Connection | None = None,
    ) -> None:
        cm = nullcontext(conn) if conn is not None else self.db.connect()

        with cm as conn:
            conn.executemany(
"""
INSERT INTO ResourceMetadata (resource_id, key, value, created_at, updated_at)
VALUES (:id, :key, :value, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT(resource_id, key) DO UPDATE SET value = :value, updated_at = CURRENT_TIMESTAMP;
""",
                [
                    {
                        "id": resource_id,
                        "key": key,
                        "value": value
                    } for resource_id, key, value in metadata
                ]
            )

    def save_resources_payloads(
        self,
        resource_payloads: Sequence[tuple[str, int, Any]],
        conn: sqlite3.Connection | None = None,
    ) -> None:
        cm = nullcontext(conn) if conn is not None else self.db.connect()

        with cm as conn:
            for resource_type, resource_id, payload in resource_payloads:
                self.payload_storage.save_payload(resource_type, resource_id, payload)
                self.set_resource_found_true(resource_type, resource_id, conn)

    def set_resource_found_true(
        self,
        resource_type: str,
        resource_id: int,
        conn: sqlite3.Connection,
    ) -> None:
        found, = conn.execute(
            "SELECT found FROM Resource WHERE id = ?",
            (resource_id,),
        ).fetchone()
        if found == 1:
            return
        conn.execute(
            "UPDATE Resource SET found = 1 WHERE id = ? AND found IS NOT 1",
            (resource_id,),
        )
        if found is None:
            self.progress.mutate_resource_found_create(resource_type)
        elif found == 0:
            self.progress.mutate_resource_not_found_delete(resource_type)
            self.progress.mutate_resource_found_create(resource_type)

    def set_resource_found_false(
        self,
        resource_type: str,
        resource_id: int,
        conn: sqlite3.Connection,
    ) -> None:
        updated = conn.execute(
            "UPDATE Resource SET found = 0 WHERE id = ? AND found IS NULL",
            (resource_id,),
        ).rowcount
        if updated:
            self.progress.mutate_resource_not_found_create(resource_type)

    def get_aliases_by_keys(
        self,
        keys: Sequence[tuple[str, str, str]],
        conn: sqlite3.Connection | None = None,
    ) -> list[tuple[int, str, str, str]]:
        unique_keys = list(set(keys))
        if not unique_keys:
            return []

        cm = nullcontext(conn) if conn is not None else self.db.connect()
        triple_chunk = SQLITE_VAR_LIMIT // 3
        rows: list[tuple[int, str, str, str]] = []

        with cm as conn:
            for offset in range(0, len(unique_keys), triple_chunk):
                batch = unique_keys[offset:offset + triple_chunk]
                rows.extend(
                    conn.execute(
f"""
SELECT resource_id, type, key, value FROM ResourceAlias
WHERE (type, key, value) IN ({','.join(['(?, ?, ?)'] * len(batch))})
""",
                        [
                            parameter
                            for key in batch
                            for parameter in key
                        ],
                    ).fetchall()
                )

        return rows

    def get_resource_aliases_and_types(
        self,
        resource_ids: Sequence[int],
        conn: sqlite3.Connection | None = None,
    ) -> tuple[dict[int, list[Alias]], dict[int, str]]:
        aliases_map: dict[int, list[Alias]] = {
            resource_id: [] for resource_id in resource_ids
        }
        types_map: dict[int, str] = {}
        if not resource_ids:
            return aliases_map, types_map

        cm = nullcontext(conn) if conn is not None else self.db.connect()

        with cm as conn:
            ids = list(resource_ids)
            for offset in range(0, len(ids), SQLITE_VAR_LIMIT):
                batch = ids[offset:offset + SQLITE_VAR_LIMIT]
                for resource_id, resource_type, key, value in conn.execute(
f"""
SELECT resource_id, type, key, value FROM ResourceAlias
WHERE resource_id IN ({','.join(['?'] * len(batch))})
ORDER BY key, value
""",
                    batch,
                ).fetchall():
                    types_map[resource_id] = resource_type
                    aliases_map[resource_id].append(Alias(key=key, value=value))

        missing = [
            resource_id for resource_id, aliases in aliases_map.items() if not aliases
        ]
        if missing:
            raise ValueError(f"Resource {missing[0]} has no aliases")
        for resource_id, aliases in aliases_map.items():
            self.require_known_aliases(types_map[resource_id], aliases)

        return aliases_map, types_map

    def count_resources(
        self,
        resource_types: list[str],
        conn: sqlite3.Connection | None = None
    ) -> int:
        cm = nullcontext(conn) if conn is not None else self.db.connect()

        with cm as conn:
            count, = conn.execute(
f"""
SELECT COUNT(*) FROM Resource
WHERE type IN ({','.join(['?'] * len(resource_types))})
""",
                resource_types
            ).fetchone()

        return count

    def load_resource_records(
        self,
        resource_ids: Sequence[int],
        conn: sqlite3.Connection | None = None,
        load_relations: bool = True,
    ) -> list[ResourceRecord]:
        if not resource_ids:
            return []

        cm = nullcontext(conn) if conn is not None else self.db.connect()

        with cm as conn:
            unique_ids = list(set(resource_ids))
            aliases_map, types_map = self.get_resource_aliases_and_types(unique_ids, conn=conn)
            if load_relations:
                resource_relations = self.get_resource_relations(unique_ids, conn=conn)
            else:
                resource_relations = {
                    resource_id: {"relations_from": {}, "relations_to": {}}
                    for resource_id in unique_ids
                }
            resource_metadata = self.get_resource_metadata(unique_ids, conn=conn)
            found_map: dict[int, bool | None] = {}
            for offset in range(0, len(unique_ids), SQLITE_VAR_LIMIT):
                batch = unique_ids[offset:offset + SQLITE_VAR_LIMIT]
                for resource_id, found in conn.execute(
f"""
SELECT id, found FROM Resource
WHERE id IN ({",".join("?" * len(batch))})
""",
                    batch,
                ):
                    found_map[resource_id] = None if found is None else bool(found)

        return [
            ResourceRecord(
                id=resource_id,
                type=types_map[resource_id],
                aliases={alias.key: alias.value for alias in aliases_map[resource_id]},
                metadata=resource_metadata[resource_id],
                relations_from=resource_relations[resource_id]["relations_from"],
                relations_to=resource_relations[resource_id]["relations_to"],
                found=found_map.get(resource_id),
                payload_loader=lambda resource_type=types_map[resource_id], resource_id=resource_id:
                    self.payload_storage.load_payload(resource_type, resource_id)
            )
            for resource_id in resource_ids
        ]
    
    def load_resources(
        self,
        resource_type: str,
        limit: int = -1,
        after_id: int = 0,
        conn: sqlite3.Connection | None = None
    ) -> list[ResourceRecord]:
        cm = nullcontext(conn) if conn is not None else self.db.connect()

        with cm as conn:
            rows = conn.execute(
"""
SELECT id FROM Resource
WHERE type = :type AND id > :after_id
ORDER BY id
LIMIT :limit
""",
                {
                    "type": resource_type,
                    "after_id": after_id,
                    "limit": limit if limit >= 0 else -1,
                }
            ).fetchall()

            return self.load_resource_records(
                [resource_id for resource_id, in rows],
                conn=conn,
            )
    
    def load_resources_from_refs(
        self,
        resource_refs: Sequence[ResourceRef],
        conn: sqlite3.Connection | None = None,
        load_relations: bool = True,
    ) -> list[ResourceRecord]:
        cm = nullcontext(conn) if conn is not None else self.db.connect()

        with cm as conn:
            return self.load_resource_records(
                self.resolve_refs(resource_refs, conn=conn),
                conn=conn,
                load_relations=load_relations,
            )
    
    def get_resource_relations(
        self,
        resource_ids: Sequence[int],
        conn: sqlite3.Connection | None = None
    ) -> dict[int, dict[str, dict[str, list[ResourceRef]]]]:
        relations_from_map: dict[int, dict[str, list[ResourceRef]]] = {
            resource_id: {}
            for resource_id in resource_ids
        }
        relations_to_map: dict[int, dict[str, list[ResourceRef]]] = {
            resource_id: {}
            for resource_id in resource_ids
        }
        if not resource_ids:
            return {}

        cm = nullcontext(conn) if conn is not None else self.db.connect()
        seen: set[tuple[str, int, int]] = set()
        relation_rows: list[tuple[str, int, int]] = []

        with cm as conn:
            ids = list(resource_ids)
            for column in ("from_resource_id", "to_resource_id"):
                for offset in range(0, len(ids), SQLITE_VAR_LIMIT):
                    batch = ids[offset:offset + SQLITE_VAR_LIMIT]
                    for relation_type, from_resource_id, to_resource_id in conn.execute(
f"""
SELECT type, from_resource_id, to_resource_id FROM ResourceRelation
WHERE {column} IN ({','.join(['?'] * len(batch))})
""",
                        batch,
                    ).fetchall():
                        row_key = (relation_type, from_resource_id, to_resource_id)
                        if row_key in seen:
                            continue
                        seen.add(row_key)
                        relation_rows.append((relation_type, from_resource_id, to_resource_id))

            related_ids = list({
                resource_id
                for _, from_resource_id, to_resource_id in relation_rows
                for resource_id in (from_resource_id, to_resource_id)
            })
            aliases_map, types_map = self.get_resource_aliases_and_types(related_ids, conn=conn)

            for (
                relation_type,
                from_resource_id,
                to_resource_id,
            ) in relation_rows:
                if from_resource_id in relations_from_map:
                    relations_from_map[from_resource_id].setdefault(relation_type, []).append(
                        ResourceRef.from_aliases(
                            types_map[to_resource_id],
                            aliases_map[to_resource_id],
                        )
                    )
                if to_resource_id in relations_to_map:
                    relations_to_map[to_resource_id].setdefault(relation_type, []).append(
                        ResourceRef.from_aliases(
                            types_map[from_resource_id],
                            aliases_map[from_resource_id],
                        )
                    )
        
        return {
            resource_id: {
                "relations_from": relations_from_map[resource_id],
                "relations_to": relations_to_map[resource_id]
            }
            for resource_id in resource_ids
        }
    
    def get_resource_metadata(
        self,
        resource_ids: Sequence[int],
        conn: sqlite3.Connection | None = None
    ) -> dict[int, dict[str, str | None]]:
        metadata_map: dict[int, dict[str, str | None]] = {
            resource_id: {}
            for resource_id in resource_ids
        }
        if not resource_ids:
            return metadata_map

        cm = nullcontext(conn) if conn is not None else self.db.connect()

        with cm as conn:
            ids = list(resource_ids)
            for offset in range(0, len(ids), SQLITE_VAR_LIMIT):
                batch = ids[offset:offset + SQLITE_VAR_LIMIT]
                for resource_id, key, value in conn.execute(
f"""
SELECT resource_id, key, value FROM ResourceMetadata
WHERE resource_id IN ({','.join(['?'] * len(batch))})
""",
                    batch
                ).fetchall():
                    metadata_map[resource_id][key] = value
        
        return metadata_map

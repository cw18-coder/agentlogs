"""Reconcile task session/creator links into a separately audited derived dataset.

Run from any directory with the EDA interpreter. Downloaded sources are read-only.
Each run creates a new folder under eda/quality_checks; only COMPLETE runs are usable.
"""

import argparse
import hashlib
import json
import logging
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pyarrow as pa
import pyarrow.parquet as pq
from agentlogs.schema import assert_dataset_version
from download_datasets import DATASET_PATH, RELEASE, REVISION

LOGGER = logging.getLogger(__name__)
IDENTITY_FIELDS = ("id", "graphql_id", "login")
OUTPUT_ROOT = Path(__file__).resolve().parent / "quality_checks"


def rows(files: list[Path], columns: list[str]):
    """Yield projected records in bounded batches."""
    for path in files:
        for batch in pq.ParquetFile(path).iter_batches(
            batch_size=4096, columns=columns
        ):
            yield from batch.to_pylist()


def fingerprint(path: Path) -> dict[str, Any]:
    """Record input/output provenance without loading entire files into memory."""
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": digest}


def build_users(files: list[Path]):
    """Index stable identities, login fallbacks, and reverse creator-task evidence."""
    users = {}
    indexes = {field: defaultdict(set) for field in IDENTITY_FIELDS}
    reverse = defaultdict(set)
    for record in rows(files, [*IDENTITY_FIELDS, "type", "tasks"]):
        user_id = record["id"]
        if user_id is None or user_id in users:
            raise ValueError(f"Missing or duplicate users.id: {user_id}")
        users[user_id] = {key: record[key] for key in (*IDENTITY_FIELDS, "type")}
        for field in IDENTITY_FIELDS:
            value = record[field]
            if value is not None and value != "":
                key = value.casefold() if field == "login" else value
                indexes[field][key].add(user_id)
        for task in record["tasks"] or []:
            if task["id"] is not None:
                reverse[task["id"]].add(user_id)
    return users, indexes, reverse


def reconcile_creator(
    task_id: str, creator: dict[str, Any] | None, users, indexes, reverse
) -> tuple[dict[str, Any] | None, str, list[str]]:
    """Repair only unambiguous creator links; retain every conflicting original."""
    original = creator or {}
    reverse_ids = reverse.get(task_id, set())
    stable = [
        field for field in ("id", "graphql_id") if original.get(field) not in (None, "")
    ]
    supplied = stable or (["login"] if original.get("login") else [])
    candidates = set()
    for field in supplied:
        value = original[field]
        key = value.casefold() if field == "login" else value
        candidates.update(indexes[field].get(key, set()))
    if len(candidates) > 1 or len(reverse_ids) > 1:
        return creator, "conflict", ["ambiguous_forward_or_reverse_identity"]
    if not candidates:
        if supplied:
            return creator, "unresolved", ["creator_not_found_in_users"]
        if not reverse_ids:
            return creator, "unresolved", ["no_creator_identity_or_reverse_link"]
        candidates = reverse_ids
        status = "recovered_from_reverse"
    else:
        status = "matched_stable" if stable else "matched_login"
    user_id = next(iter(candidates))
    canonical = users[user_id]
    if any(original[field] != canonical[field] for field in stable):
        return creator, "conflict", ["stable_identifiers_disagree"]
    if reverse_ids and user_id not in reverse_ids:
        return creator, "conflict", ["creator_disagrees_with_users_tasks"]
    updated = dict(original)
    for field in IDENTITY_FIELDS:
        updated[field] = canonical[field]
    if not updated.get("type"):
        updated["type"] = canonical["type"]
    flags = [] if user_id in reverse_ids else ["user_reverse_task_link_missing"]
    return updated, status, flags


def build_sessions(files: list[Path]):
    """Treat sessions.task.id as the authority for the derived session lists."""
    by_task = defaultdict(list)
    owners = {}
    for record in rows(files, ["id", "task", "session_index"]):
        session_id = record["id"]
        task_id = (record["task"] or {}).get("id")
        index = record["session_index"]
        if not session_id or not task_id or index is None:
            raise ValueError("Session lacks a required id, task.id, or session_index.")
        if session_id in owners:
            raise ValueError(f"Duplicate sessions.id: {session_id}")
        owners[session_id] = task_id
        by_task[task_id].append({"id": session_id, "session_index": index})
    for references in by_task.values():
        references.sort(key=lambda ref: (ref["session_index"], ref["id"]))
    return by_task, owners


def session_changes(before, after, task_id, owners) -> dict[str, Any]:
    """Explain list changes, including dangling and wrongly owned references."""
    old = before or []
    old_ids = {ref["id"] for ref in old}
    new_ids = {ref["id"] for ref in after}
    return {
        "added_ids": sorted(new_ids - old_ids),
        "absent_from_sessions": [ref["id"] for ref in old if ref["id"] not in owners],
        "belongs_to_other_task": [
            ref["id"]
            for ref in old
            if ref["id"] in owners and owners[ref["id"]] != task_id
        ],
        "duplicates_removed": len(old) - len(old_ids),
        "before": before,
        "after": after,
    }


def write_journal(run_path: Path, summary: dict[str, Any]) -> None:
    """Produce the requested human-readable EDA journal with exact run counts."""
    counts = "\n".join(
        f"* `{key}`: {value:,}" for key, value in sorted(summary["counts"].items())
    )
    text = f"""---
title: "EDA journal: task-session and task-user reconciliation"
description: "Conservative derived-copy repair with source provenance and unresolved-link flags."
date: "{summary["started_utc"][:10]}"
---

## Run and provenance

* Started UTC: {summary["started_utc"]}
* Release: `{RELEASE}`
* Immutable revision: `{REVISION}`
* Input directory: `{summary["input_directory"]}`
* Status: COMPLETE

Exact source file SHA-256 hashes and sizes are recorded in [summary.json](./summary.json).
All source hashes were checked again after processing. No source files were modified.

## Rationale and rules

Rebuild each task's entire session list from `agent_sessions.task.id`, ordered by
`session_index` then session ID. This fills empty lists and missing links, removes
references absent from sessions or owned by a different task, removes duplicate
references, and updates indices without renumbering them. Empty derived lists mean
no matching session row in this snapshot, not no real-world execution.

Tasks have a single `creator`, not a user list. Match stable numeric/GraphQL IDs
first. Use case-insensitive login only when both stable IDs are absent. Recover a
creator with no identity only from a unique `users.tasks` reverse reference.
For a confirmed match, fill canonical identity fields from users; preserve existing
nonempty creator type. Preserve unresolved or conflicting creator structs unchanged.
A stable ID that is present but unmatched never falls back to login or reverse links.

Users' reverse task lists are corroborating evidence, not authority for overwriting
a conflicting creator. Missing reverse links are flagged. Users and sessions are not
rewritten. Session-user identity is not assumed to identify the task's creator.

## Results

{counts}

Counts of statuses/reasons can overlap. Session-link counts count references;
task counts count source task rows. Zero-valued metrics are retained in the summary.

## Outputs and validation

* [Derived task Parquet](./agent_tasks/part_00000_of_00001.parquet)
* [Per-task audit](./task_audit.jsonl), one row per task including unchanged tasks
* [Orphan-link audit](./orphan_links.jsonl), session/reverse-user links to absent tasks
* [Machine-readable summary and provenance](./summary.json)

The task row count, row order, schema, and all fields except `sessions` and `creator`
are preserved. Every derived session reference exists in sessions and points back
to its owning task by construction. The output is read back and validated before
this run is marked COMPLETE. Creator conflicts remain unresolved, not cleaned away.

## Interpretation limits and next steps

The derived dataset prioritizes local referential consistency. Missing target rows
can reflect collection/API gaps, so removed references remain in the audit.
Inspect unresolved/conflicting creator rows before excluding cases from analysis.
Use this derived copy explicitly; do not substitute it silently for the raw release.
Only runs with `summary.json` status COMPLETE are usable. A failed run folder may
contain partial files and is not a validated output.
"""
    (run_path / "eda_journal.md").write_text(text, encoding="utf-8")


def reconcile(input_path: Path, output_root: Path) -> Path:
    """Create a new, non-overwriting, audited run from the three raw tables."""
    assert_dataset_version(input_path)
    files = {
        name: sorted((input_path / name).glob("*.parquet"))
        for name in ("agent_tasks", "agent_sessions", "users")
    }
    if any(not shards for shards in files.values()):
        raise FileNotFoundError(
            "agent_tasks, agent_sessions, and users shards are required."
        )
    if (
        input_path.resolve() == output_root.resolve()
        or input_path.resolve() in output_root.resolve().parents
    ):
        raise ValueError("Output must be outside the raw input directory.")
    started = datetime.now(UTC).isoformat()
    run_path = output_root / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8]
    )
    run_path.mkdir(parents=True, exist_ok=False)
    LOGGER.info("Run output: %s (not complete until summary.json is written)", run_path)
    source_manifest = [
        fingerprint(path) for shards in files.values() for path in shards
    ]
    users, indexes, reverse = build_users(files["users"])
    sessions, owners = build_sessions(files["agent_sessions"])
    schema = pq.read_schema(files["agent_tasks"][0])
    counts = Counter(
        {
            key: 0
            for key in (
                "tasks",
                "tasks_sessions_changed",
                "tasks_creator_changed",
                "empty_session_lists_before",
                "empty_session_lists_filled",
                "empty_session_lists_after",
                "session_references_added",
                "session_references_absent_removed",
                "wrong_owner_references_removed",
                "duplicate_session_references_removed",
                "tasks_creator_unresolved",
                "tasks_creator_conflict",
                "session_rows_to_absent_tasks",
                "reverse_user_links_to_absent_tasks",
            )
        }
    )
    seen = set()
    destination = run_path / "agent_tasks" / "part_00000_of_00001.parquet"
    destination.parent.mkdir()
    with (
        pq.ParquetWriter(destination, schema, compression="zstd") as writer,
        (run_path / "task_audit.jsonl").open("w", encoding="utf-8") as audit,
    ):
        for path in files["agent_tasks"]:
            if not pq.read_schema(path).equals(schema, check_metadata=True):
                raise ValueError(f"Task shard schema differs: {path}")
            for batch in pq.ParquetFile(path).iter_batches(batch_size=4096):
                new_sessions, new_creators = [], []
                for task in batch.select(["id", "sessions", "creator"]).to_pylist():
                    task_id = task["id"]
                    if not task_id or task_id in seen:
                        raise ValueError(f"Missing or duplicate tasks.id: {task_id}")
                    seen.add(task_id)
                    before = task["sessions"]
                    after = sessions.get(task_id, [])
                    changes = session_changes(before, after, task_id, owners)
                    creator, status, flags = reconcile_creator(
                        task_id, task["creator"], users, indexes, reverse
                    )
                    session_changed = before != after
                    creator_changed = creator != task["creator"]
                    counts["tasks"] += 1
                    counts["tasks_sessions_changed"] += session_changed
                    counts["tasks_creator_changed"] += creator_changed
                    counts["empty_session_lists_before"] += not before
                    counts["empty_session_lists_filled"] += not before and bool(after)
                    counts["empty_session_lists_after"] += not after
                    counts["session_references_added"] += len(changes["added_ids"])
                    counts["session_references_absent_removed"] += len(
                        changes["absent_from_sessions"]
                    )
                    counts["wrong_owner_references_removed"] += len(
                        changes["belongs_to_other_task"]
                    )
                    counts["duplicate_session_references_removed"] += changes[
                        "duplicates_removed"
                    ]
                    counts[f"tasks_creator_{status}"] += 1
                    for flag in flags:
                        counts[f"creator_flag_{flag}"] += 1
                    audit.write(
                        json.dumps(
                            {
                                "task_id": task_id,
                                "sessions_changed": session_changed,
                                "sessions": changes if session_changed else None,
                                "creator_status": status,
                                "creator_flags": flags,
                                "creator_changed": creator_changed,
                                "creator_before": task["creator"],
                                "creator_after": creator,
                                "reverse_user_ids": sorted(reverse.get(task_id, set())),
                            }
                        )
                        + "\n"
                    )
                    new_sessions.append(after)
                    new_creators.append(creator)
                table = pa.Table.from_batches([batch], schema=schema)
                for name, values in (
                    ("sessions", new_sessions),
                    ("creator", new_creators),
                ):
                    field = schema.field(name)
                    table = table.set_column(
                        schema.get_field_index(name),
                        field,
                        pa.array(values, type=field.type),
                    )
                writer.write_table(table)
    with (run_path / "orphan_links.jsonl").open("w", encoding="utf-8") as audit:
        for session_id, task_id in owners.items():
            if task_id not in seen:
                counts["session_rows_to_absent_tasks"] += 1
                audit.write(
                    json.dumps(
                        {
                            "kind": "session",
                            "task_id": task_id,
                            "session_id": session_id,
                        }
                    )
                    + "\n"
                )
        for task_id, user_ids in reverse.items():
            if task_id not in seen:
                counts["reverse_user_links_to_absent_tasks"] += len(user_ids)
                audit.write(
                    json.dumps(
                        {
                            "kind": "users.tasks",
                            "task_id": task_id,
                            "user_ids": sorted(user_ids),
                        }
                    )
                    + "\n"
                )

    LOGGER.info("Validating written task data and source immutability.")
    output = pq.ParquetFile(destination)
    if output.metadata.num_rows != counts["tasks"] or not output.schema_arrow.equals(
        schema
    ):
        raise ValueError("Output row count or schema changed.")
    original_batches = (
        batch
        for path in files["agent_tasks"]
        for batch in pq.ParquetFile(path).iter_batches(batch_size=4096)
    )
    # Align record boundaries independently of source shard and output row-group sizes.
    original = pa.Table.from_batches(original_batches, schema=schema)
    derived = output.read()
    unchanged = [name for name in schema.names if name not in ("sessions", "creator")]
    if not original.select(unchanged).equals(derived.select(unchanged)):
        raise ValueError("An unrelated task field or row order changed.")
    for task in derived.select(["id", "sessions"]).to_pylist():
        if task["sessions"] != sessions.get(task["id"], []):
            raise ValueError(f"Derived session list validation failed: {task['id']}")
    for record in source_manifest:
        if fingerprint(Path(record["path"])) != record:
            raise ValueError(f"Source file changed during processing: {record['path']}")
    summary = {
        "status": "COMPLETE",
        "started_utc": started,
        "completed_utc": datetime.now(UTC).isoformat(),
        "input_directory": str(input_path.resolve()),
        "release": RELEASE,
        "revision": REVISION,
        "counts": dict(counts),
        "sources": source_manifest,
        "script": fingerprint(Path(__file__)),
        "outputs": [fingerprint(destination)],
    }
    write_journal(run_path, summary)
    (run_path / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    LOGGER.info("COMPLETE: %s", json.dumps(dict(counts), sort_keys=True))
    return run_path


def main() -> int:
    """Run the conservative reconciliation with explicit errors and no overwrites."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DATASET_PATH)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        reconcile(args.input_dir, args.output_root)
        return 0
    except (OSError, ValueError, pa.ArrowException) as exc:
        LOGGER.error("Reconciliation failed; any partial run is NOT COMPLETE: %s", exc)
        return 1
    except KeyboardInterrupt:
        LOGGER.error("Interrupted; any partial run is NOT COMPLETE.")
        return 130


if __name__ == "__main__":
    sys.exit(main())

"""Synthetic regression tests using the release's actual Arrow schemas."""

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import reconcile_tasks as quality

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "dataset-sample"


def write_records(root: Path, name: str, records: list[dict]) -> None:
    schema = pq.read_schema(next((SAMPLE / name).glob("*.parquet")))
    folder = root / name
    folder.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        pa.Table.from_pylist(records, schema=schema), folder / "part.parquet"
    )


@pytest.fixture
def fixture_data(tmp_path: Path) -> Path:
    root = tmp_path / "raw"
    root.mkdir()
    (root / "VERSION").write_bytes((SAMPLE / "VERSION").read_bytes())
    task_base = pq.read_table(
        next((SAMPLE / "agent_tasks").glob("*.parquet"))
    ).to_pylist()[0]
    session_base = pq.read_table(
        next((SAMPLE / "agent_sessions").glob("*.parquet"))
    ).to_pylist()[0]
    user_base = pq.read_table(next((SAMPLE / "users").glob("*.parquet"))).to_pylist()[0]
    user1 = dict(
        user_base,
        id=1,
        graphql_id="U1",
        login="alice",
        tasks=[{"id": "T1"}, {"id": "T3"}],
    )
    user2 = dict(user_base, id=2, graphql_id="U2", login="bob", tasks=[{"id": "T2"}])
    write_records(root, "users", [user1, user2])
    write_records(
        root,
        "agent_sessions",
        [
            dict(session_base, id="S1", task={"id": "T1"}, session_index=2),
            dict(session_base, id="S2", task={"id": "T2"}, session_index=0),
            dict(session_base, id="ORPHAN", task={"id": "ABSENT"}, session_index=0),
        ],
    )
    empty_creator = {"id": None, "graphql_id": None, "login": None, "type": None}
    write_records(
        root,
        "agent_tasks",
        [
            dict(task_base, id="T1", sessions=[], creator=empty_creator),
            dict(
                task_base,
                id="T2",
                sessions=[
                    {"id": "MISSING", "session_index": 0},
                    {"id": "S1", "session_index": 1},
                    {"id": "S2", "session_index": 9},
                    {"id": "S2", "session_index": 9},
                ],
                creator={
                    "id": 2,
                    "graphql_id": "U2",
                    "login": "old_bob",
                    "type": "User",
                },
            ),
            dict(
                task_base,
                id="T3",
                sessions=[],
                creator={"id": 2, "graphql_id": "U2", "login": "bob", "type": "User"},
            ),
        ],
    )
    return root


def test_full_repair_provenance_and_idempotence(
    fixture_data: Path, tmp_path: Path
) -> None:
    before = {p: p.read_bytes() for p in fixture_data.rglob("*") if p.is_file()}
    run = quality.reconcile(fixture_data, tmp_path / "out")
    result_file = run / "agent_tasks" / "part_00000_of_00001.parquet"
    table = pq.read_table(result_file)
    result = table.to_pylist()
    assert result[0]["sessions"] == [{"id": "S1", "session_index": 2}]
    assert result[0]["creator"]["id"] == 1
    assert result[1]["sessions"] == [{"id": "S2", "session_index": 0}]
    assert result[1]["creator"]["login"] == "bob"
    assert (
        result[2]["creator"]["id"] == 2
    )  # Reverse conflict is retained, not overwritten.
    assert all(path.read_bytes() == contents for path, contents in before.items())
    summary = json.loads((run / "summary.json").read_text())
    assert summary["status"] == "COMPLETE"
    counts = summary["counts"]
    assert counts["empty_session_lists_filled"] == 1
    assert counts["session_references_absent_removed"] == 1
    assert counts["wrong_owner_references_removed"] == 1
    assert counts["duplicate_session_references_removed"] == 1
    assert counts["tasks_creator_conflict"] == 1
    assert counts["session_rows_to_absent_tasks"] == 1
    audit = [
        json.loads(line) for line in (run / "task_audit.jsonl").read_text().splitlines()
    ]
    assert len(audit) == 3
    assert audit[2]["creator_flags"] == ["creator_disagrees_with_users_tasks"]
    assert (run / "eda_journal.md").is_file()
    original_schema = pq.read_schema(
        next((fixture_data / "agent_tasks").glob("*.parquet"))
    )
    assert table.schema.equals(original_schema)
    write_records(fixture_data, "agent_tasks", result)
    again = quality.reconcile(fixture_data, tmp_path / "out")
    assert run != again
    second = json.loads((again / "summary.json").read_text())
    assert second["counts"]["tasks_sessions_changed"] == 0
    assert second["counts"]["tasks_creator_changed"] == 0


def test_creator_matching_rules(fixture_data: Path) -> None:
    users, indexes, reverse = quality.build_users(
        sorted((fixture_data / "users").glob("*.parquet"))
    )
    creator = {"id": 999, "graphql_id": None, "login": "alice", "type": "User"}
    updated, status, _ = quality.reconcile_creator(
        "X", creator, users, indexes, reverse
    )
    assert status == "unresolved" and updated == creator
    creator = {"id": 1, "graphql_id": "U2", "login": "alice", "type": "User"}
    updated, status, _ = quality.reconcile_creator(
        "X", creator, users, indexes, reverse
    )
    assert status == "conflict" and updated == creator
    creator = {"id": None, "graphql_id": None, "login": "ALICE", "type": None}
    updated, status, flags = quality.reconcile_creator(
        "X", creator, users, indexes, reverse
    )
    assert status == "matched_login" and updated["id"] == 1
    assert flags == ["user_reverse_task_link_missing"]
    reverse["X"] = {1, 2}
    updated, status, _ = quality.reconcile_creator(
        "X", creator, users, indexes, reverse
    )
    assert status == "conflict" and updated == creator


def test_duplicate_session_id_aborts(fixture_data: Path, tmp_path: Path) -> None:
    records = pq.read_table(
        next((fixture_data / "agent_sessions").glob("*.parquet"))
    ).to_pylist()
    write_records(fixture_data, "agent_sessions", [records[0], records[0]])
    with pytest.raises(ValueError, match="Duplicate sessions.id"):
        quality.reconcile(fixture_data, tmp_path / "out")
    assert not list((tmp_path / "out").rglob("summary.json"))


def test_output_inside_raw_rejected(fixture_data: Path) -> None:
    with pytest.raises(ValueError, match="outside"):
        quality.reconcile(fixture_data, fixture_data / "derived")

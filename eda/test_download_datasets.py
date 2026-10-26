"""Tests for download selection, validation, and cache-preserving configuration."""

from pathlib import Path
from unittest.mock import Mock

import download_datasets as downloader
import pytest
from huggingface_hub import DatasetInfo
from huggingface_hub.hf_api import RepoSibling


def dataset_info() -> DatasetInfo:
    files = [
        RepoSibling(rfilename=f"{table}/part_00000.parquet", size=4)
        for table in sorted(downloader.TABLES)
    ]
    files.extend(
        RepoSibling(rfilename=name, size=4) for name in sorted(downloader.SUPPORT_FILES)
    )
    files.extend(
        [
            RepoSibling(rfilename="agent_tasks/part_00001.parquet", size=4),
            RepoSibling(rfilename="README.md", size=4),
        ]
    )
    info = DatasetInfo(id=downloader.DATASET_ID, sha=downloader.REVISION)
    info.siblings = files
    return info


@pytest.mark.parametrize("include_logs", [False, True])
def test_selects_all_shards_and_support_files(include_logs: bool) -> None:
    files = downloader.select_files(dataset_info(), include_logs=include_logs)
    names = {item.rfilename for item in files}
    assert downloader.SUPPORT_FILES <= names
    assert "agent_tasks/part_00001.parquet" in names
    assert "README.md" not in names
    assert ("agent_session_logs/part_00000.parquet" in names) == include_logs
    assert len(names) == (11 if include_logs else 10)


def test_rejects_unexpected_revision() -> None:
    info = dataset_info()
    info.sha = "different-commit"
    with pytest.raises(ValueError, match="Unexpected dataset revision"):
        downloader.select_files(info, include_logs=False)


@pytest.mark.parametrize("missing", ["VERSION", "users/part_00000.parquet"])
def test_rejects_incomplete_inventory(missing: str) -> None:
    info = dataset_info()
    info.siblings = [item for item in info.siblings if item.rfilename != missing]
    with pytest.raises(ValueError, match="missing required"):
        downloader.select_files(info, include_logs=False)


def test_rejects_missing_size() -> None:
    info = dataset_info()
    next(item for item in info.siblings if item.rfilename == "VERSION").size = None
    with pytest.raises(ValueError, match="File-size metadata"):
        downloader.select_files(info, include_logs=False)


def test_dry_run_does_not_download_or_create_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    api = Mock()
    api.dataset_info.return_value = dataset_info()
    snapshot = Mock()
    destination = tmp_path / "not-created"
    monkeypatch.setattr(downloader, "HfApi", Mock(return_value=api))
    monkeypatch.setattr(downloader, "snapshot_download", snapshot)
    monkeypatch.setattr(downloader, "DATASET_PATH", destination)
    assert downloader.main(["--dry-run"]) == 0
    snapshot.assert_not_called()
    assert not destination.exists()
    api.dataset_info.assert_called_once_with(
        downloader.DATASET_ID, revision=downloader.REVISION, files_metadata=True
    )


@pytest.mark.parametrize("include_logs", [False, True])
def test_download_uses_pinned_shared_cache_and_validates_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, include_logs: bool
) -> None:
    info = dataset_info()
    api = Mock()
    api.dataset_info.return_value = info
    files = downloader.select_files(info, include_logs=include_logs)
    for item in files:
        target = tmp_path / item.rfilename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"data")
    snapshot = Mock()
    validate = Mock()
    monkeypatch.setattr(downloader, "HfApi", Mock(return_value=api))
    monkeypatch.setattr(downloader, "snapshot_download", snapshot)
    monkeypatch.setattr(downloader, "assert_dataset_version", validate)
    monkeypatch.setattr(downloader, "DATASET_PATH", tmp_path)

    assert downloader.main(["--include-logs"] if include_logs else []) == 0
    snapshot.assert_called_once_with(
        repo_id=downloader.DATASET_ID,
        repo_type="dataset",
        revision=downloader.REVISION,
        allow_patterns=[item.rfilename for item in files],
        local_dir=tmp_path,
        force_download=False,
        max_workers=4,
    )
    validate.assert_called_once_with(tmp_path)


def test_invalid_download_is_reported_as_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    api = Mock()
    api.dataset_info.return_value = dataset_info()
    monkeypatch.setattr(downloader, "HfApi", Mock(return_value=api))
    monkeypatch.setattr(downloader, "snapshot_download", Mock())
    monkeypatch.setattr(downloader, "DATASET_PATH", tmp_path)
    assert downloader.main([]) == 1
    assert "missing or size mismatch" in caplog.text

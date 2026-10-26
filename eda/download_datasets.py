"""Download the pinned AgentLogs tables into the notebook's existing data directory.

Run with the EDA interpreter. Logs are excluded unless --include-logs is supplied.
Hugging Face's local metadata cache reuses unchanged files on subsequent runs.
"""

import argparse
import logging
import sys
from pathlib import Path

from agentlogs.schema import assert_dataset_version
from huggingface_hub import DatasetInfo, HfApi, snapshot_download
from huggingface_hub.errors import HfHubHTTPError
from huggingface_hub.hf_api import RepoSibling

LOGGER = logging.getLogger(__name__)
DATASET_ID = "risenlab/agentlogs"
RELEASE = "1.0-20261008"
REVISION = "25549ec57745fdf174620c1e75d7fd02d9c4dc22"
REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = REPO_ROOT / "data" / "eda" / RELEASE / REVISION
TABLES = {
    "repositories",
    "agent_tasks",
    "agent_sessions",
    "agent_session_logs",
    "users",
    "pull_requests",
    "pull_request_timelines",
    "workflow_runs",
}
LOG_TABLE = "agent_session_logs"
SUPPORT_FILES = {"VERSION", "DATA_LICENSE"}


def create_parser() -> argparse.ArgumentParser:
    """Define the explicit opt-in for the large session-log table."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-logs",
        action="store_true",
        help="Also download agent_session_logs (approximately 63 GB).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch metadata and print the file plan without downloading dataset files.",
    )
    return parser


def select_files(info: DatasetInfo, *, include_logs: bool) -> list[RepoSibling]:
    """Select every shard of the requested tables and require a complete inventory."""
    if info.sha != REVISION:
        raise ValueError(
            f"Unexpected dataset revision: {info.sha}; expected {REVISION}."
        )
    requested = TABLES if include_logs else TABLES - {LOG_TABLE}
    files = [
        item
        for item in info.siblings or []
        if item.rfilename in SUPPORT_FILES
        or (
            item.rfilename.endswith(".parquet")
            and item.rfilename.split("/")[0] in requested
        )
    ]
    found_tables = {
        item.rfilename.split("/")[0]
        for item in files
        if item.rfilename.endswith(".parquet")
    }
    missing = (requested - found_tables) | (
        SUPPORT_FILES - {item.rfilename for item in files}
    )
    if missing:
        raise ValueError(
            f"Pinned dataset is missing required tables/files: {sorted(missing)}"
        )
    if any(item.size is None for item in files):
        raise ValueError(
            "File-size metadata is missing; cannot validate the download plan."
        )
    return sorted(files, key=lambda item: item.rfilename)


def main(argv: list[str] | None = None) -> int:
    """Download the selected immutable snapshot and validate its files and schema."""
    args = create_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        info = HfApi().dataset_info(DATASET_ID, revision=REVISION, files_metadata=True)
        files = select_files(info, include_logs=args.include_logs)
        LOGGER.info(
            "Dataset: %s; release: %s; commit: %s", DATASET_ID, RELEASE, REVISION
        )
        LOGGER.info("Destination: %s", DATASET_PATH)
        LOGGER.info(
            "Session logs: %s",
            "INCLUDED (approximately 63 GB)" if args.include_logs else "excluded",
        )
        for item in files:
            target = DATASET_PATH / item.rfilename
            LOGGER.info(
                "%s | %s bytes | %s",
                item.rfilename,
                f"{item.size:,}",
                "present; Hub cache will verify reuse"
                if target.is_file()
                else "not present",
            )
        total_bytes = sum(item.size for item in files if item.size is not None)
        LOGGER.info(
            "Selected size: %.3f GB (decimal); existing cached files reduce actual transfer.",
            total_bytes / 1_000_000_000,
        )
        if args.dry_run:
            LOGGER.info("Dry run complete; no dataset files downloaded.")
            return 0

        snapshot_download(
            repo_id=DATASET_ID,
            repo_type="dataset",
            revision=REVISION,
            allow_patterns=[item.rfilename for item in files],
            local_dir=DATASET_PATH,
            force_download=False,
            max_workers=4,
        )
        for item in files:
            target = DATASET_PATH / item.rfilename
            if not target.is_file() or target.stat().st_size != item.size:
                raise ValueError(f"Downloaded file missing or size mismatch: {target}")
        assert_dataset_version(DATASET_PATH)
        LOGGER.info(
            "Ready: all %s selected files are present and schema-compatible.",
            len(files),
        )
        return 0
    except (HfHubHTTPError, OSError, ValueError) as exc:
        LOGGER.error("Download failed: %s", exc)
        return 1
    except KeyboardInterrupt:
        LOGGER.error(
            "Interrupted. Rerun the same command to reuse completed downloads."
        )
        return 130


if __name__ == "__main__":
    sys.exit(main())

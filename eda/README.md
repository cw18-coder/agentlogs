---
title: "AgentLogs exploratory data analysis"
description: "Reproducible local Python environment for exploratory notebooks."
---

## Environment

Keep exploratory notebooks in this directory. The local virtual environment is
`.venv`, with CPython 3.12.13 x64 pinned in [.python-version](./.python-version).
This interpreter runs through x64 emulation on the current Windows ARM64 machine.
The existing repository ignore rules exclude the virtual environment from Git.

[pyproject.toml](./pyproject.toml) declares direct dependencies, and
[uv.lock](./uv.lock) records resolved versions. The AgentLogs schema package is
installed in editable mode from
[the repository package](../packages/risenlab-agentlogs/), constrained to
`~=1.0.0`, as supported by the repository README. Changes to that local package
therefore affect this environment without reinstalling it.

The environment includes:

* `risenlab-agentlogs` and `huggingface_hub` for schema validation and dataset access
* `duckdb`, `pyarrow`, and `pandas` for Parquet queries and data exploration
* `numpy`, `matplotlib`, and `seaborn` for numerical analysis and visualization
* `ipykernel` and `ipywidgets` for VS Code notebooks and widgets
* `tqdm` for progress reporting
* `ruff` and `pytest` for development checks
* `pip` for conventional package inspection and notebook `%pip` support

Polars is intentionally omitted following the compatibility assessment and user
decision. The tested standard and compatibility runtimes failed their CPU check
under x64 emulation. Native ARM64 resolution could not supply the tested PyArrow
version. No CPU checks or TLS verification were disabled.

## Recreate or synchronize

From the repository root in PowerShell:

```powershell
uv sync --project .\eda --locked
```

Run commands without activating the environment:

```powershell
uv run --project .\eda --locked python --version
uv pip check --python .\eda\.venv\Scripts\python.exe
.\eda\.venv\Scripts\python.exe -m pip check
```

Optional activation:

```powershell
.\eda\.venv\Scripts\Activate.ps1
```

Use `uv add --project .\eda <package>` for future dependency changes so the
manifest, lockfile, and environment remain synchronized. Ad hoc `%pip install`
commands do not update the uv dependency files.

The local AgentLogs source avoids a missing package-metadata artifact encountered
on the configured package mirror. Public PyPI downloads also encountered a TLS
handshake failure during setup. Other dependencies installed from the configured
mirror; no global package-manager configuration was changed. Recreating the
environment requires access to the locked package sources.

## VS Code notebooks

Open a notebook, select its kernel, and choose the interpreter at
`.venv\Scripts\python.exe` within this directory. An environment-local kernelspec
named `AgentLogs EDA (Python 3.12)` is also installed; it is not registered globally.
If VS Code does not discover the display name, select the interpreter directly.

After recreating the environment, the optional named kernel can be reinstalled:

```powershell
.\eda\.venv\Scripts\python.exe -m ipykernel install --prefix .\eda\.venv --name agentlogs-eda --display-name "AgentLogs EDA (Python 3.12)"
```

## Data

### Download the pinned tables

[download_datasets.py](./download_datasets.py) uses the same dataset ID, release,
immutable commit, and destination as the introductory notebook. It downloads all
seven non-log tables by default, plus `VERSION` and `DATA_LICENSE`.

From the repository root:

```powershell
.\eda\.venv\Scripts\python.exe .\eda\download_datasets.py --dry-run
.\eda\.venv\Scripts\python.exe .\eda\download_datasets.py
```

Session logs require explicit opt-in and add approximately 63 GB:

```powershell
.\eda\.venv\Scripts\python.exe .\eda\download_datasets.py --include-logs
```

Files are stored under
`data\eda\1.0-20261008\25549ec57745fdf174620c1e75d7fd02d9c4dc22`,
in one subdirectory per table. The destination is resolved relative to the
script, so it does not depend on your terminal's working directory.

Rerunning uses Hugging Face's existing `.cache\huggingface` metadata in that
directory and does not force downloads. Unchanged files, including the task shard
already downloaded by the notebook, are reused. Remote metadata requests may
still occur. Preserve the cache metadata; a bare file-existence check is not
sufficient to establish the file's version. Downloads validate file sizes and
the schema marker before reporting success. Errors are explicit and return a
nonzero exit status; rerunning after interruption reuses completed downloads.

The dry run lists selected files and total selected size, not an exact estimate
of remaining network transfer. It downloads no dataset payloads.

### Reconcile task relationships

[reconcile_tasks.py](./reconcile_tasks.py) checks task-session and task-creator
relationships against the locally downloaded sessions and users tables.

```powershell
.\eda\.venv\Scripts\python.exe .\eda\reconcile_tasks.py
```

Each run creates a new timestamped folder under `eda\quality_checks`, containing
the derived `agent_tasks` Parquet, a complete per-task JSONL audit, orphan-link
audit, summary with source hashes, and an `eda_journal.md` detailing rules and
results. Local derived data and identifiable audit records are Git-ignored.
Use only runs whose `summary.json` reports COMPLETE. Raw files are not modified.

Session lists are rebuilt from `agent_sessions.task.id`, preserving source
session indices. Creators are matched by stable identity, using login only if
stable identifiers are absent; missing identities can be recovered from a unique
`users.tasks` reverse link. Unresolved or conflicting creators are retained and
flagged, not erased. Existing confirmed login identities are refreshed from users.
Only `sessions` and `creator` may change; task rows, order, schema, and other
fields are validated unchanged. No user/session table is rewritten.

Alternate local inputs and output roots can be passed using `--input-dir` and
`--output-root`. The input must have the release schema marker and all three
tables. No network access is used. Missing target rows can be collection gaps,
so removed references are evidence-preserving audit changes, not proof of
nonexistent activity.

### Explore the tables

Start with [01_agent_tasks_eda.ipynb](./01_agent_tasks_eda.ipynb) for a guided
exploration of the task table. Running its acquisition cell downloads only the
pinned task Parquet shard (about 83.7 MB) and schema marker, not the full dataset.
It also offers an explicitly selected offline demonstration-sample mode.

No full dataset download is part of environment setup. Start with the bundled
[sample](../data/dataset-sample/) to check schemas and queries. It is a
demonstration sample, not a representative or statistically sufficient pilot.

When downloading research data, pin release `1.0-20261008` rather than `main`,
and validate its schema with `agentlogs.schema.assert_dataset_version`.
Notebook working directories can vary; locate the repository root explicitly
before constructing relative data paths.

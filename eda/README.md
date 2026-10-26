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

No full dataset download is part of environment setup. Start with the bundled
[sample](../data/dataset-sample/) to check schemas and queries. It is a
demonstration sample, not a representative or statistically sufficient pilot.

When downloading research data, pin release `1.0-20261008` rather than `main`,
and validate its schema with `agentlogs.schema.assert_dataset_version`.
Notebook working directories can vary; locate the repository root explicitly
before constructing relative data paths.

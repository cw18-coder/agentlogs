from datetime import date

from common import setup_state, EXPORT_PATH
from agentlogs.schema import __version__
from agentlogs.collector.export import (
    RepositoryExporter, 
    TaskExporter, 
    SessionExporter, 
    UserExporter, 
    SessionLogExporter,
    WorkflowRunExporter,
    PullRequestExporter,
    PullRequestTimelineExporter,
)

state = setup_state()

export_path = EXPORT_PATH / "repositories"
exporter = RepositoryExporter(state, export_path)
exporter.export(shard_size=400_000, batch_size=200_000)

export_path = EXPORT_PATH / "agent_tasks"
exporter = TaskExporter(state, export_path)
exporter.export(shard_size=400_000, batch_size=200_000)

export_path = EXPORT_PATH / "agent_sessions"
exporter = SessionExporter(state, export_path)
exporter.export(shard_size=250_000, batch_size=125_000)

export_path = EXPORT_PATH / "agent_session_logs"
exporter = SessionLogExporter(state, export_path)
exporter.export(shard_size=150_000, batch_size=30_000)

export_path = EXPORT_PATH / "pull_requests"
exporter = PullRequestExporter(state, export_path)
exporter.export(shard_size=75_000, batch_size=37_500)

export_path = EXPORT_PATH / "pull_request_timelines"
exporter = PullRequestTimelineExporter(state, export_path)
exporter.export(shard_size=2_500_000, batch_size=500_000)

export_path = EXPORT_PATH / "workflow_runs"
exporter = WorkflowRunExporter(state, export_path)
exporter.export(shard_size=800_000, batch_size=400_000)

export_path = EXPORT_PATH / "users"
exporter = UserExporter(state, export_path)
exporter.export(shard_size=300_000, batch_size=150_000)

(EXPORT_PATH / "VERSION").write_text(
    f"{__version__}-{date.today():%Y%m%d}\n",
    encoding="utf-8",
)

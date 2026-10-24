from pathlib import Path

from .runtime import ProcessorGroup, ResolveGraphql, ResolveRest, Runner, Scheduler
from .state import State
from .steps import (
    CollectPullRequestTimeline,
    CollectRepositoryTasks,
    CollectSessionLog,
    CollectTask,
    CollectWorkflowRun,
    SeedRepositories,
)


def seed_scheduler(
    state: State,
    csv_path: str | Path,
    chunk_size: int = 50000,
) -> Scheduler:
    return Scheduler(
        state,
        runners=[
            Runner(
                state,
                [SeedRepositories(csv_path=str(csv_path), chunk_size=chunk_size)],
                n_workers=1,
            )
        ],
    )


def collect_scheduler(
    state: State,
    github_api,
    github_graphql_api,
    copilot_api,
    *,
    github_workers: int = 80,
    copilot_workers: int = 10,
    show_token_dashboard: bool = True,
) -> Scheduler:
    return Scheduler(
        state,
        runners=[
            Runner(
                state,
                n_workers=github_workers,
                description="Collecting GitHub API",
                groups=[
                    ProcessorGroup(
                        [
                            CollectRepositoryTasks(github_api),
                            CollectWorkflowRun(github_api),
                            CollectPullRequestTimeline(github_api, state),
                            ResolveRest(github_api, state),
                        ],
                        share=0.7,
                        token_store=github_api.token_store,
                        wallet="rest",
                    ),
                    ProcessorGroup(
                        [ResolveGraphql(github_graphql_api, state)],
                        share=0.3,
                        token_store=github_api.token_store,
                        wallet="graphql",
                    ),
                ],
            ),
            Runner(
                state,
                [CollectTask(copilot_api), CollectSessionLog(copilot_api)],
                n_workers=copilot_workers,
                description="Collecting Copilot API",
            ),
        ],
        token_stores=[github_api.token_store, copilot_api.token_store],
        show_token_dashboard=show_token_dashboard,
    )

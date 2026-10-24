import asyncio
import sys

from common import SEED_PATH, setup_state
from agentlogs.collector import SeedRepositoriesJobDraft, seed_scheduler
from agentlogs.collector.priorities import PRIORITIES

# Front-load the collection with some repositories with a lot of tasks,
# to make sure the Copilot and GraphQL API have enough work.
PRIORITY_REPOSITORIES = [
    "github/gh-aw",
    "microsoft/vscode",
    "dotnet/runtime",
    "musicmonk42/The_Code_Factory_Working_V2",
    "github/gh-aw-mcpg",
    "mlflow/mlflow",
    "github/gh-aw-firewall",
    "camunda/camunda",
    "kubestellar/console",
    "azure/azure-sdk-for-net",
]


async def run(init: bool = False):
    state = setup_state(create_db=init)

    with state.db:
        if init:
            state.create_jobs([SeedRepositoriesJobDraft()])

        await seed_scheduler(state, SEED_PATH).run()

        priority = PRIORITIES["collect_repository_tasks"] + 1
        with state.db.connect() as conn:
            updated = conn.execute(
                f"""
                UPDATE Job
                SET priority = ?, updated_at = CURRENT_TIMESTAMP
                WHERE type IN ('collect_repository_tasks', 'collect_repository_tasks_archived')
                  AND status IN ('queued', 'running', 'failed')
                  AND resource_id IN (
                    SELECT resource_id
                    FROM ResourceAlias
                    WHERE type = 'repository'
                      AND key = 'full_name'
                      AND value IN ({",".join("?" * len(PRIORITY_REPOSITORIES))})
                  )
                """,
                [priority, *PRIORITY_REPOSITORIES],
            ).rowcount
        print(f"set {updated} repository listing jobs to priority {priority}")


def main():
    asyncio.run(run(init="--init" in sys.argv))


if __name__ == "__main__":
    main()

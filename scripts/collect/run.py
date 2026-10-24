import asyncio
import sys

from common import (
    setup_github_api,
    setup_github_graphql_api,
    setup_copilot_api,
    setup_state,
)
from agentlogs.collector import collect_scheduler


async def run(hide_tokens: bool = False):
    state = setup_state()
    github_api, copilot_api = setup_github_api(), setup_copilot_api()
    github_graphql_api = setup_github_graphql_api(github_api.token_store)

    with state.db:
        await collect_scheduler(
            state,
            github_api,
            github_graphql_api,
            copilot_api,
            show_token_dashboard=not hide_tokens,
        ).run()


def main():
    asyncio.run(run(hide_tokens="--hide-tokens" in sys.argv))


if __name__ == "__main__":
    main()

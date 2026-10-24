import datetime as dt
from pathlib import Path
import tomllib

import agentlogs.collector.state as collector_state
from agentlogs.collector.state import State, Database, PayloadStorage
from agentlogs.collector.api import (
    GitHubRestAPI,
    CopilotRestAPI,
    TokenStore,
    GitHubGraphQLAPI,
    WalletSpec,
)

ROOT = Path(__file__).resolve().parents[2]
API_TOKENS_PATH = ROOT / "api_tokens.toml"
DATA_PATH = ROOT / "data"
SEED_PATH = DATA_PATH / "seed_repositories.csv"
PAYLOAD_PATH = DATA_PATH / "collect"
DB_PATH = DATA_PATH / "collect" / "state.db"
EXPORT_PATH = DATA_PATH / "dataset"


def setup_state(create_db: bool = False) -> State:
    return State(
        Database(
            DB_PATH,
            pool_size=20,
            create=create_db,
            schema_path=Path(collector_state.__file__).resolve().parents[1] / "state_schema.sql"
        ),
        PayloadStorage(PAYLOAD_PATH)
    )

def setup_github_token_store() -> TokenStore:
    with open(API_TOKENS_PATH, "rb") as f:
        api_tokens = tomllib.load(f)

    return TokenStore(
        [
            (token["name"], token["token"])
            for token in api_tokens["github"]
        ],
        description="GitHub API",
        wallets={
            "rest": WalletSpec(limit=60, cooldown=dt.timedelta(minutes=1, seconds=2)),
            "graphql": WalletSpec(limit=5000),
        },
        exclusive={"rest", "graphql"},
    )


def setup_github_api(token_store: TokenStore | None = None) -> GitHubRestAPI:
    return GitHubRestAPI(token_store if token_store is not None else setup_github_token_store())


def setup_copilot_api() -> CopilotRestAPI:
    with open(API_TOKENS_PATH, "rb") as f:
        api_tokens = tomllib.load(f)

    return CopilotRestAPI(TokenStore(
        [
            (token["name"], token["token"])
            for token in api_tokens["copilot"]
        ],
        description="Copilot API",
        wallets={"rest": WalletSpec(limit=20, cooldown=dt.timedelta(seconds=1))},
    ))


def setup_github_graphql_api(token_store: TokenStore | None = None) -> GitHubGraphQLAPI:
    return GitHubGraphQLAPI(token_store if token_store is not None else setup_github_token_store())
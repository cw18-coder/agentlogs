import httpx
from collections.abc import Mapping
from typing import Any
import datetime as dt

from .tokens import TokenStore
from .errors import (
    APIError,
    RateLimitError,
    NotFoundError,
    MaxAttemptsRecoverableError,
    RecoverableError,
)


class GraphQLAPI:
    def __init__(
        self,
        token_store: TokenStore,
        url: str,
        headers: dict[str, Any] | None = None,
    ):
        self.token_store = token_store
        self.url = url
        self.headers = headers or {}
        self.client = httpx.AsyncClient(
            http2=True,
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=100,
            ),
            timeout=httpx.Timeout(
                connect=5.0,
                read=30.0,
                write=10.0,
                pool=5.0,
            ),
        )

    async def request(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        estimated_cost: int = 1,
    ) -> dict[str, Any]:

        token = self.token_store.get_token(
            "graphql",
            cost=estimated_cost,
        )

        headers = {
            **self.headers,
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            response = await self.client.post(
                self.url,
                headers=headers,
                json={
                    "query": query,
                    "variables": variables or {},
                },
            )

        except httpx.HTTPError as e:
            self.apply_response_rate_limits(token, estimated_cost)
            raise RecoverableError(e)

        self.apply_response_rate_limits(token, estimated_cost, response.headers)

        if response.status_code == 499:
            raise RecoverableError("Client closed request")

        if response.status_code == 502:
            raise RecoverableError("Bad gateway")

        if response.status_code == 503:
            raise RecoverableError("Service unavailable")

        if response.status_code == 504:
            raise RecoverableError("Gateway timeout")

        if response.status_code == 401:
            self.token_store.backoff(token, "graphql")
            raise RateLimitError(f"Bad credentials, token {token[:6]}")

        if response.status_code == 403:
            if "retry-after" in response.headers:
                self.token_store.retry_after(
                    token,
                    "graphql",
                    dt.timedelta(
                        seconds=int(
                            response.headers["retry-after"]
                        )
                    ),
                )
                raise RateLimitError(
                    "GraphQL secondary rate limit"
                )

            if "limit" in response.text.lower():
                self.token_store.backoff(token, "graphql")
                raise RateLimitError(
                    "GraphQL secondary rate limit"
                )

            self.token_store.backoff(token, "graphql")
            raise MaxAttemptsRecoverableError(
                f"Forbidden, possibly invalid token or connection issue (token {token[:6]})",
                max_attempts=10,
            )

        if response.status_code == 451:
            raise NotFoundError("Resource not found")

        if response.status_code != 200:
            raise APIError(
                f"GraphQL request failed "
                f"{response.status_code}: "
                f"{response.text}"
            )

        body = response.json()

        if "errors" in body:
            for error in body["errors"]:
                error_type = error.get("type")
                message = error.get("message", "")

                if error_type in {"RATE_LIMITED", "RATE_LIMIT"}:
                    self.token_store.backoff(token, "graphql")

                    raise RateLimitError(message)

                if error_type == "NOT_FOUND":
                    raise NotFoundError(message)

                if error_type == "INTERNAL":
                    if message.startswith(
                        "Something went wrong while executing your query"
                    ):
                        raise MaxAttemptsRecoverableError(message, max_attempts=3)
                    raise RecoverableError(message)

            raise APIError(str(body["errors"]))

        self.token_store.reset_backoff(token)
        self.token_store.add_success(token, "graphql")

        return body

    def apply_response_rate_limits(
        self,
        token: str,
        cost: int,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self.token_store.release(token, "graphql", cost)
        found = {key.lower(): value for key, value in headers.items()} if headers is not None else {}
        if "x-ratelimit-remaining" not in found:
            return
        remaining = int(found["x-ratelimit-remaining"])
        if "x-ratelimit-limit" in found:
            self.token_store.set_limit(token, "graphql", int(found["x-ratelimit-limit"]))
        budget = self.token_store.token_wallet(token, "graphql")
        self.token_store.set_remaining(token, "graphql", remaining - budget.in_flight)
        if "x-ratelimit-reset" in found:
            self.token_store.set_reset_time(
                token,
                "graphql",
                dt.datetime.fromtimestamp(int(found["x-ratelimit-reset"]), tz=dt.timezone.utc),
            )

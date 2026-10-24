import datetime as dt
from collections.abc import Mapping
from typing import Any

import httpx

from .errors import (
    APIError,
    MaxAttemptsRecoverableError,
    NotFoundError,
    RecoverableError,
    RateLimitError,
)
from .tokens import TokenStore

class RestAPI:
    token_store: TokenStore
    headers: dict[str, str]
    client: httpx.AsyncClient

    def __init__(self, token_store: TokenStore, headers: dict[str, str]):
        self.token_store = token_store
        self.headers = headers

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
        url: str,
        headers: dict[str, Any] = {},
    ) -> httpx.Response:
        token = self.token_store.get_token("rest", cost=1)

        headers = {
            **self.headers,
            **headers,
            "Authorization": f"Bearer {token}",
        }

        try:
            response = await self.client.get(url, headers=headers)
        except httpx.HTTPError as e:
            self.apply_response_rate_limits(token, 1)
            raise RecoverableError(e)

        self.apply_response_rate_limits(token, 1, response.headers)
        
        if response.status_code == 200:
            self.token_store.reset_backoff(token)
            self.token_store.add_success(token, "rest")
            return response
        
        elif response.status_code == 401:
            self.token_store.backoff(token, "rest")
            raise RateLimitError(f"Bad credentials, possibly invalid token or connection issue (token {token[:6]})")
        
        # Treat 301 (redirect) as not found, since we cannot handle e.g. repository renames
        elif response.status_code == 301 or response.status_code == 404 or response.status_code == 410 or response.status_code == 451:
            raise NotFoundError(f"Resource not found")
        
        elif response.status_code == 500:
            raise RecoverableError(f"Internal server error")
        
        elif response.status_code == 502:
            raise RecoverableError(f"Bad gateway")
        
        elif response.status_code == 503:
            raise RecoverableError(f"Service unavailable")
        
        elif response.status_code == 504:
            raise RecoverableError(f"Gateway timeout")

        elif response.status_code == 499:
            raise RecoverableError(f"Client closed request")
        
        elif response.status_code == 403 or response.status_code == 429:
            if response.headers.get("X-RateLimit-Remaining") == "0" and "X-RateLimit-Reset" in response.headers:
                reset_time = dt.datetime.fromtimestamp(
                    int(response.headers["X-RateLimit-Reset"]),
                    tz=dt.timezone.utc
                )
                self.token_store.set_reset_time(token, "rest", reset_time + dt.timedelta(seconds=3))
                raise RateLimitError("Rate limit exceeded, retry at specified reset time")
            
            elif "Retry-After" in response.headers:
                retry_after = dt.timedelta(seconds=int(response.headers["Retry-After"]))
                self.token_store.retry_after(token, "rest", retry_after + dt.timedelta(seconds=.5))
                raise RateLimitError("Rate limit exceeded, retry after specified time")
            
            elif response.status_code == 429 or 'limit' in response.text.lower():
                self.token_store.backoff(token, "rest")
                raise RateLimitError("Rate limit exceeded, retry after backoff time")
            
            elif response.status_code == 403:
                self.token_store.backoff(token, "rest")
                raise MaxAttemptsRecoverableError(
                    f"Forbidden, possibly invalid token or connection issue (token {token[:6]})",
                    max_attempts=10,
                )
        
        raise APIError(f"Request failed with status code {response.status_code}: {response.text}")

    def apply_response_rate_limits(
        self,
        token: str,
        cost: int,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self.token_store.release(token, "rest", cost)
        if headers is None:
            return
        found = {key.lower(): value for key, value in headers.items()}
        if "x-ratelimit-remaining" not in found:
            return
        remaining = int(found["x-ratelimit-remaining"])
        reset_at = None
        if "x-ratelimit-reset" in found:
            reset_at = dt.datetime.fromtimestamp(
                int(found["x-ratelimit-reset"]),
                tz=dt.timezone.utc,
            )
        budget = self.token_store.token_wallet(token, "rest")
        if remaining == 0:
            self.token_store.set_remaining(token, "rest", 0)
            if reset_at is not None:
                self.token_store.set_reset_time(token, "rest", reset_at)
            return
        if remaining < budget.remaining:
            self.token_store.set_remaining(token, "rest", remaining)

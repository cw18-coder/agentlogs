from dataclasses import dataclass, field
import datetime as dt
from collections.abc import Collection, Mapping

from ..datetime import get_utc_max, get_utc_min, get_utc_now
from .errors import NoAvailableTokenError


@dataclass(frozen=True)
class WalletSpec:
    limit: int
    cooldown: dt.timedelta | None = None
    ramp_interval: dt.timedelta | None = None
    ramp_factor: float = 1.5


@dataclass
class TokenWallet:
    limit: int
    remaining: int
    in_flight: int = 0
    running: int = 0
    success: int = 0
    reset_at: dt.datetime = field(default_factory=get_utc_min)
    rate_limited_at: dt.datetime = field(default_factory=get_utc_min)
    blocked_until: dt.datetime = field(default_factory=get_utc_min)
    cooldown: dt.timedelta | None = None
    configured: int = 0
    maximum: int = 0
    ramp_interval: dt.timedelta | None = None
    ramp_factor: float = 1.5
    ramp_ceiling: int | None = None
    ramp_until: dt.datetime = field(default_factory=get_utc_min)

    def refill_if_due(self) -> None:
        if self.remaining == 0 and self.reset_at <= get_utc_now():
            self.remaining = self.limit

    def is_available(self, cost: int) -> bool:
        self.refill_if_due()
        return self.blocked_until <= get_utc_now() and self.remaining >= cost

    def available_at(self) -> dt.datetime:
        self.refill_if_due()
        if self.remaining == 0:
            return max(self.blocked_until, self.reset_at)
        return self.blocked_until


@dataclass
class TokenInfo:
    token: str
    wallets: dict[str, TokenWallet]
    backoff: int = 0
    success: int = 0


class TokenStore:
    def __init__(
        self,
        tokens: list[tuple[str, str]],
        description: str = "Token Store",
        *,
        wallets: Mapping[str, WalletSpec],
        exclusive: Collection[str] = (),
    ):
        if not wallets:
            raise ValueError(f"{description} needs at least one wallet")
        self.description = description
        self.tokens = [token for _, token in tokens]
        self.token_names = [name for name, _ in tokens]
        self.wallets = dict(wallets)
        self.exclusive = set(exclusive)
        self.last_used: dict[str, str] = {}
        self.token_infos = {
            token: TokenInfo(
                token=token,
                wallets={
                    name: TokenWallet(
                        limit=spec.limit,
                        remaining=spec.limit,
                        cooldown=spec.cooldown,
                        configured=spec.limit,
                        maximum=spec.limit,
                        ramp_interval=spec.ramp_interval,
                        ramp_factor=spec.ramp_factor,
                    )
                    for name, spec in self.wallets.items()
                },
            )
            for token in self.tokens
        }

    def token_wallet(self, token: str, wallet: str) -> TokenWallet:
        return self.token_infos[token].wallets[wallet]

    def has_available_token(self, wallet: str, cost: int = 1) -> bool:
        return any(
            self.token_wallet(token, wallet).is_available(cost)
            for token in self.tokens
        )

    def get_token(self, wallet: str, cost: int = 1) -> str:
        return self.reserve({wallet: cost})

    def reserve(self, costs: Mapping[str, int]) -> str:
        for token in self.tokens:
            for name in costs:
                self.advance_ramp(token, name)
        available = [
            token
            for token in self.tokens
            if all(
                self.token_wallet(token, name).is_available(cost)
                for name, cost in costs.items()
            )
        ]
        if not available:
            now = get_utc_now()
            ready_at = []
            for token in self.tokens:
                ready = now
                for name, cost in costs.items():
                    budget = self.token_wallet(token, name)
                    if not budget.is_available(cost):
                        ready = max(ready, budget.available_at())
                ready_at.append(ready)
            raise NoAvailableTokenError(reset_time=min(ready_at))
        if set(costs) < self.exclusive:
            idle = [
                token
                for token in available
                if all(
                    self.token_wallet(token, wallet).running == 0
                    for wallet in self.exclusive - set(costs)
                )
            ]
        else:
            idle = available
        bottleneck = max(costs, key=lambda name: costs[name])
        token = min(
            idle or available,
            key=lambda item: self.token_wallet(item, bottleneck).remaining,
        )
        for name, cost in costs.items():
            self.last_used[name] = token
            budget = self.token_wallet(token, name)
            budget.remaining -= cost
            budget.in_flight += cost
            budget.running += 1
            if budget.remaining == 0 and budget.cooldown is not None and budget.reset_at <= get_utc_now():
                now = get_utc_now()
                budget.rate_limited_at = now
                budget.reset_at = now + budget.cooldown
        return token

    def set_limit(self, token: str, wallet: str, limit: int) -> None:
        budget = self.token_wallet(token, wallet)
        if budget.ramp_interval is None:
            budget.limit = limit
            return
        budget.maximum = min(budget.configured, limit)
        self.advance_ramp(token, wallet)
        if budget.ramp_ceiling is None:
            budget.limit = limit
            return
        budget.limit = min(limit, budget.ramp_ceiling)

    def set_remaining(self, token: str, wallet: str, remaining: int) -> None:
        budget = self.token_wallet(token, wallet)
        if budget.ramp_ceiling is not None:
            self.advance_ramp(token, wallet)
            remaining = min(remaining, budget.ramp_ceiling)
        budget.remaining = remaining

    def start_ramp(self, token: str, wallet: str) -> None:
        budget = self.token_wallet(token, wallet)
        observed = max(0, budget.limit - max(budget.remaining, 0))
        ceiling = observed if observed > 0 else max(1, budget.limit // 2)
        budget.ramp_ceiling = min(ceiling, budget.maximum)
        budget.ramp_until = get_utc_now() + budget.ramp_interval
        if budget.limit > budget.ramp_ceiling:
            budget.limit = budget.ramp_ceiling
        if budget.remaining > budget.ramp_ceiling:
            budget.remaining = budget.ramp_ceiling

    def advance_ramp(self, token: str, wallet: str) -> None:
        budget = self.token_wallet(token, wallet)
        if budget.ramp_interval is None or budget.ramp_ceiling is None:
            return
        now = get_utc_now()
        ceiling = budget.ramp_ceiling
        until = budget.ramp_until
        while now >= until and ceiling < budget.maximum:
            increased = int(ceiling * budget.ramp_factor)
            if increased <= ceiling:
                increased = ceiling + 1
            ceiling = min(budget.maximum, increased)
            until += budget.ramp_interval
        budget.ramp_ceiling = ceiling
        budget.ramp_until = until
        if budget.limit > ceiling:
            budget.limit = ceiling
        if budget.remaining > ceiling:
            budget.remaining = ceiling

    def release(self, token: str, wallet: str, cost: int) -> None:
        budget = self.token_wallet(token, wallet)
        budget.in_flight -= cost
        budget.running -= 1
        if budget.in_flight < 0 or budget.running < 0:
            raise ValueError(f"{wallet} in_flight dropped below 0 for token {token[:6]}")

    def set_reset_time(
        self,
        token: str,
        wallet: str,
        reset_at: dt.datetime,
    ) -> None:
        budget = self.token_wallet(token, wallet)
        now = get_utc_now()
        if reset_at > budget.reset_at:
            if now > budget.reset_at:
                budget.rate_limited_at = now
            budget.reset_at = reset_at

    def retry_after(
        self,
        token: str,
        wallet: str,
        retry_after: dt.timedelta,
    ) -> None:
        budget = self.token_wallet(token, wallet)
        now = get_utc_now()
        latest = get_utc_max() - dt.timedelta(seconds=1)
        try:
            until = now + retry_after
        except OverflowError:
            until = latest
        else:
            if until > latest:
                until = latest
        if until > budget.blocked_until:
            if get_utc_now() > budget.blocked_until:
                budget.rate_limited_at = get_utc_now()
            budget.blocked_until = until

    def backoff(self, token: str, wallet: str) -> None:
        info = self.token_infos[token]
        info.backoff = min(info.backoff + 1, 16)
        self.retry_after(
            token,
            wallet,
            dt.timedelta(seconds=2 ** info.backoff),
        )

    def reset_backoff(self, token: str) -> None:
        self.token_infos[token].backoff = 0

    def add_success(self, token: str, wallet: str) -> None:
        self.token_infos[token].success += 1
        self.token_wallet(token, wallet).success += 1

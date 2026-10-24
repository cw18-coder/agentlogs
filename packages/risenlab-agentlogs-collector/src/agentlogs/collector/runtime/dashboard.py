import asyncio
import datetime as dt
import time

from rich import box
from tqdm.std import EMA
from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.table import Table
from rich.text import Text

from .runner import Runner
from ..datetime import format_timedelta, get_utc_now
from ..api import TokenStore
from ..state import State, ResourceRef


class ProgressRate:
    mininterval = 1.0
    smoothing = 0.01

    def __init__(self, n: int, at: float):
        self.n = n
        self.at = at
        self.dn = EMA(self.smoothing)
        self.dt = EMA(self.smoothing)

    def observe(self, n: int, at: float) -> float | None:
        if n < self.n:
            self.n = n
            self.at = at
            self.dn = EMA(self.smoothing)
            self.dt = EMA(self.smoothing)
            return None
        dn = n - self.n
        dt = at - self.at
        if dn > 0 and dt >= self.mininterval:
            self.dn(dn)
            self.dt(dt)
            self.n = n
            self.at = at
        if not self.dt.calls:
            return None
        return self.dn() / self.dt()


class Dashboard:
    def __init__(
        self,
        state: State,
        runners: list[Runner],
        token_stores: list[TokenStore],
        refresh: float = 0.1,
    ):
        self.state = state
        self.runners = runners
        self.token_stores = token_stores
        self.refresh = refresh
        self.running = False
        self.console = Console()
        self.job_rates: dict[tuple[str, str], ProgressRate] = {}
        self.resource_rates: dict[str, ProgressRate] = {}

    async def run(self):
        if self.running:
            raise RuntimeError("Dashboard already running")

        self.running = True
        try:
            with Live(self.render(), console=self.console, refresh_per_second=max(1, int(1 / self.refresh))) as live:
                while True:
                    live.update(self.render())
                    await asyncio.sleep(self.refresh)
        except asyncio.CancelledError:
            pass
        finally:
            self.running = False

    def render(self) -> Group:
        parts: list[RenderableType] = [self.resource_table()]
        shown_stores: set[int] = set()
        half = max(40, self.console.width // 2)
        for runner in self.runners:
            by_wallet = {group.wallet: group for group in runner.groups if group.wallet}
            if "rest" in by_wallet and "graphql" in by_wallet:
                row = Table.grid(expand=True, padding=(0, 1))
                row.add_column(ratio=1)
                row.add_column(ratio=1)
                row.add_row(
                    self.job_table("GH REST", by_wallet["rest"].job_types, runner, half),
                    self.job_table("GH GraphQL", by_wallet["graphql"].job_types, runner, half),
                )
                parts.append(row)
                store = by_wallet["rest"].token_store
                if store is not None and store in self.token_stores:
                    parts.append(self.token_table(store))
                    shown_stores.add(id(store))
            else:
                row = Table.grid(expand=True, padding=(0, 1))
                row.add_column(ratio=1)
                row.add_column(ratio=1)
                row.add_row(
                    self.job_table(runner.description, runner.job_types, runner, half),
                    Text(""),
                )
                parts.append(row)
        for store in self.token_stores:
            if id(store) not in shown_stores:
                parts.append(self.token_table(store))
        return Group(*parts)

    def job_table(self, title: str, job_types: list[str], runner: Runner, width: int) -> Table:
        table = Table(
            title=title,
            width=width,
            padding=(0, 1),
            pad_edge=False,
            box=box.SIMPLE_HEAD,
        )
        table.add_column("jobs", no_wrap=True, overflow="ellipsis", ratio=1)
        table.add_column("progress", no_wrap=True)
        table.add_column("it/s", justify="right", no_wrap=True)
        table.add_column("eta", justify="right", no_wrap=True)
        table.add_column(
            f"{'running':>7} {'canceled':>8} {'fail':>6}".replace(" ", "\u00a0"),
            no_wrap=True,
            justify="right",
        )
        rows: list[tuple[str, list[str]]] = [
            ("overall", job_types),
        ]
        if len(job_types) > 1:
            rows.extend((job_type, [job_type]) for job_type in job_types)
        now = time.monotonic()
        counted: list[tuple[str, int, int, int, int, int, float | None]] = []
        for description, types in rows:
            counts = self.state.progress.get_job_types_status_counts(types)
            finished = counts.completed + counts.failed
            total = counts.total - counts.canceled
            rate = self.job_rates.setdefault(
                (title, description),
                ProgressRate(finished, now),
            ).observe(finished, now)
            counted.append((
                description,
                finished,
                total,
                counts.running,
                counts.canceled,
                counts.failed,
                rate,
            ))
        count_width = max((len(f"{finished}/{total}") for _, finished, total, _, _, _, _ in counted), default=1)
        for description, finished, total, running, canceled, failed, rate in counted:
            label = description
            if description == "overall" and runner.status.idle:
                label = "overall (idle)"
            per_second, eta = self.rate_and_eta(rate, max(0, total - finished))
            count = f"{finished}/{total}".rjust(count_width).replace(" ", "\u00a0")
            table.add_row(
                label,
                f"{self.bar(finished, total, width=8)} {count}",
                per_second,
                eta,
                f"{running:7d} {canceled:8d} {failed:6d}".replace(" ", "\u00a0"),
            )
        return table

    def resource_table(self) -> Table:
        table = Table(
            title="resources",
            expand=True,
            padding=(0, 1),
            pad_edge=False,
            box=box.SIMPLE_HEAD,
        )
        table.add_column("type", no_wrap=True, overflow="ellipsis", ratio=1)
        table.add_column("progress", no_wrap=True)
        table.add_column("it/s", justify="right", no_wrap=True)
        table.add_column("eta", justify="right", no_wrap=True)
        table.add_column("not_found", justify="right", no_wrap=True)
        types = sorted(
            set(ResourceRef._registry) | set(self.state.progress.resource_counts)
        )
        now = time.monotonic()
        rows: list[tuple[str, int, int, int, float | None]] = []
        for resource_type in types:
            total = self.state.progress.resource_counts.get(resource_type, 0)
            not_found = self.state.progress.resource_not_found_counts.get(resource_type, 0)
            found = self.state.progress.resource_found_counts.get(resource_type, 0)
            current = found + not_found
            rate = self.resource_rates.setdefault(resource_type, ProgressRate(current, now)).observe(current, now)
            rows.append((resource_type, current, total, not_found, rate))
        count_width = max((len(f"{current}/{total}") for _, current, total, _, _ in rows), default=1)
        for resource_type, current, total, not_found, rate in rows:
            remaining = max(0, total - current)
            per_second, eta = self.rate_and_eta(rate, remaining)
            count = f"{current}/{total}".rjust(count_width).replace(" ", "\u00a0")
            table.add_row(
                resource_type,
                f"{self.bar(current, total)} {count}",
                per_second,
                eta,
                str(not_found),
            )
        return table

    def rate_and_eta(self, rate: float | None, remaining: int) -> tuple[str, str]:
        if rate and remaining > 0:
            seconds = remaining / rate
            if seconds <= dt.timedelta.max.total_seconds():
                eta = format_timedelta(dt.timedelta(seconds=seconds))
            else:
                eta = f"{'—':>8}"
        elif remaining == 0:
            eta = format_timedelta(dt.timedelta(0))
        else:
            eta = f"{'—':>8}"
        return f"{rate or 0:5.2f}", eta

    def token_table(self, store: TokenStore) -> RenderableType:
        now = get_utc_now()
        pairs = list(zip(store.tokens, store.token_names))
        names = set(store.wallets)
        if names != {"rest", "graphql"}:
            wallet = next(iter(store.wallets))
            table = self.token_wallet_table(store, None, pairs, wallet, now)
            return Group(Text(f"{store.description} ({len(store.tokens)} tokens)"), table)
        mid = (len(pairs) + 1) // 2
        halves = (pairs[:mid], pairs[mid:])
        columns = [
            self.token_wallet_table(store, f"REST {index}/2", half, "rest", now)
            for index, half in enumerate(halves, start=1)
        ]
        columns.extend(
            self.token_wallet_table(store, f"GraphQL {index}/2", half, "graphql", now)
            for index, half in enumerate(halves, start=1)
        )
        row = Table.grid(expand=True, padding=(0, 1))
        for _ in columns:
            row.add_column(ratio=1)
        row.add_row(*columns)
        return Group(Text(f"{store.description} ({len(store.tokens)} tokens)"), row)

    def token_wallet_table(
        self,
        store: TokenStore,
        title: str | None,
        pairs: list[tuple[str, str]],
        wallet: str,
        now: dt.datetime,
    ) -> Table:
        table = Table(
            title=title,
            expand=True,
            padding=(0, 1),
            pad_edge=False,
            box=box.SIMPLE_HEAD,
        )
        table.add_column("token", no_wrap=True, overflow="ellipsis", ratio=1)
        table.add_column("limit", no_wrap=True)
        table.add_column("running", no_wrap=True, justify="right")
        table.add_column("success", no_wrap=True, justify="right")
        table.add_column("wait", no_wrap=True, justify="right")
        for token, name in pairs:
            budget = store.token_wallet(token, wallet)
            label = Text(name)
            quota = Text(
                f"{self.bar(budget.remaining, budget.limit, width=6)} {budget.remaining:4d}/{budget.limit}".replace(" ", "\u00a0")
            )
            running = Text(f"{budget.running:7d}".replace(" ", "\u00a0"))
            success = Text(f"{budget.success:7d}".replace(" ", "\u00a0"))
            wait = Text(format_timedelta(max(budget.available_at() - now, dt.timedelta(seconds=0))))
            cells = (label, quota, running, success, wait)
            if not budget.is_available(1):
                for cell in cells:
                    cell.stylize("red")
            elif store.last_used.get(wallet) == token:
                for cell in cells:
                    cell.stylize("blue")
            table.add_row(*cells)
        return table

    def bar(self, current: int, total: int, width: int = 16) -> str:
        if total <= 0:
            filled = 0
        else:
            filled = max(0, min(width, int(width * current / total)))
        return f"[{'█' * filled}{'░' * (width - filled)}]"

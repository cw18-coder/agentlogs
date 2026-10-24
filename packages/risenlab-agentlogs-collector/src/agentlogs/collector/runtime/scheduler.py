import asyncio

from .runner import Runner
from .dashboard import Dashboard
from ..api import TokenStore
from ..state import State

class Scheduler:
    state: State
    runners: list[Runner]
    token_stores: list[TokenStore]
    show_token_dashboard: bool
    started: bool = False

    def __init__(
        self,
        state: State,
        runners: list[Runner],
        token_stores: list[TokenStore] = [],
        show_token_dashboard: bool = True,
    ):
        self.state = state
        self.runners = runners
        self.token_stores = token_stores
        self.show_token_dashboard = show_token_dashboard

    async def run(self):
        if self.started:
            raise RuntimeError("Scheduler is already running")
        self.started = True

        self.state.progress.initialize()

        dashboard = Dashboard(
            self.state,
            self.runners,
            self.token_stores if self.show_token_dashboard else [],
            refresh=0.2,
        )

        async with asyncio.TaskGroup() as tg:
            runner_tasks = [
                tg.create_task(runner.run())
                for runner in self.runners
            ]
            dashboard_task = tg.create_task(dashboard.run())
            tg.create_task(self.monitor(dashboard_task, runner_tasks))

        
    async def monitor(self, dashboard_task: asyncio.Task[None], runner_tasks: list[asyncio.Task[None]]):
        while True:
            if (all(
                runner.status.idle and
                runner.status.last_seen_queue_generation == self.state.queue_generation
                for runner in self.runners
            )):
                break

            await asyncio.sleep(1)

        dashboard_task.cancel()
        for task in runner_tasks:
            task.cancel()
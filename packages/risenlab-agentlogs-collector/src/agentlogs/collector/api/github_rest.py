from typing import Any
from urllib.parse import quote

from .responses import PullRequest, TimelineEvent, User, WorkflowRun
from .rest import RestAPI
from .tokens import TokenStore

class GitHubRestAPI(RestAPI):
    API_URL = "https://api.github.com"
    API_VERSION = "2026-03-10"

    def __init__(self, token_store: TokenStore):
        super().__init__(token_store, headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.API_VERSION,
        })

    async def request_user_from_id(self, user_id: int) -> User:
        response = await self.request(f"{self.API_URL}/user/{user_id}")
        return response.json()

    async def request_user_from_login(self, login: str) -> User:
        response = await self.request(
            f"{self.API_URL}/users/{quote(login, safe='')}"
        )
        return response.json()
    
    async def request_tasks(
        self, 
        repository: str, 
        archived: bool, 
        since: str, 
        page_size: int
    ) -> list[dict[str, Any]]:
        owner, name = repository.split("/", 1)
        response = await self.request(
            f"{self.API_URL}/agents/repos/{quote(owner, safe='')}/{quote(name, safe='')}/tasks"
            f"?per_page={page_size}"
            f"&is_archived={'true' if archived else 'false'}"
            f"&since={since}"
            f"&sort=updated_at"
            f"&direction=asc"
        )
        return response.json()["tasks"]

    async def request_repository_from_id(
        self,
        repository_id: int,
    ) -> dict[str, Any]:
        response = await self.request(f"{self.API_URL}/repositories/{repository_id}")
        return response.json()
    
    async def request_sessions(
        self, 
        task_id: str
    ) -> list[dict[str, Any]]:
        response = await self.request(f"{self.API_URL}/agents/tasks/{quote(task_id, safe='')}")
        return response.json()["sessions"]

    async def request_pr(self, repository: str, number: int) -> PullRequest:
        owner, name = repository.split("/", 1)
        response = await self.request(
            f"{self.API_URL}/repos/{quote(owner, safe='')}/{quote(name, safe='')}/pulls/{number}"
        )
        return response.json()

    async def request_issue_timeline(
        self,
        repository: str,
        number: int,
        page: int = 1,
    ) -> list[TimelineEvent]:
        owner, name = repository.split("/", 1)
        response = await self.request(
            f"{self.API_URL}/repos/{quote(owner, safe='')}/{quote(name, safe='')}"
            f"/issues/{number}/timeline?per_page=100&page={page}"
        )
        batch = response.json()
        if not isinstance(batch, list):
            raise ValueError("issue timeline must be a list")
        return batch

    async def request_workflow_run(
        self,
        repository: str,
        run_id: int,
    ) -> WorkflowRun:
        owner, name = repository.split("/", 1)
        response = await self.request(
            f"{self.API_URL}/repos/{quote(owner, safe='')}/{quote(name, safe='')}/actions/runs/{run_id}"
        )
        return response.json()

    async def request_workflow_run_jobs(
        self,
        repository: str,
        run_id: int,
        page: int = 1,
        page_size: int = 100,
    ) -> dict[str, Any]:
        owner, name = repository.split("/", 1)
        response = await self.request(
            f"{self.API_URL}/repos/{quote(owner, safe='')}/{quote(name, safe='')}/actions/runs/{run_id}/jobs"
            f"?per_page={page_size}&page={page}"
        )
        return response.json()

    async def request_branch(
        self,
        repository: str,
        name: str,
    ) -> dict[str, Any]:
        owner, repo = repository.split("/", 1)
        response = await self.request(
            f"{self.API_URL}/repos/{quote(owner, safe='')}/{quote(repo, safe='')}/branches/{quote(name, safe='')}"
        )
        return response.json()

from typing import Any

from httpx_sse import EventSource

from .rest import RestAPI
from .tokens import TokenStore

class CopilotRestAPI(RestAPI):
    API_URL = "https://api.githubcopilot.com"
    
    def __init__(self, token_store: TokenStore):
        super().__init__(token_store, headers={
            "Accept": "application/json",
        })
        
    async def request_session_log(self, session_id: str) -> list[dict[str, Any]]:
        response = await self.request(f'{self.API_URL}/agents/sessions/{session_id}/logs', headers={
            'Accept': 'text/event-stream',
        })

        log = []
        event_source = EventSource(response)
        async for event in event_source.aiter_sse():
            log.append(event.data)

        return log
        
    async def request_task_detailed(self, task_id: str) -> dict[str , Any]:
        response = await self.request(f'{self.API_URL}/agents/tasks/{task_id}')
        return response.json()

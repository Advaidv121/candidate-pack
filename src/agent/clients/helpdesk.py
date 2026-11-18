from time import monotonic, sleep

import httpx

from agent.schemas import Action, PostBody


class HelpdeskClient:
    """Read tickets and submit decisions to the helpdesk."""

    def __init__(self, client: httpx.Client):
        self.client = client
        self._next_request = 0.0

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        sleep(max(0, self._next_request - monotonic()))
        self._next_request = monotonic() + 0.25
        return self.client.request(method, path, **kwargs)

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        if response.status_code == 429:
            return max(0, float(response.headers.get("Retry-After", "1")))
        return 0.5 * 2 ** attempt

    def _get(self, path: str, **params) -> dict:
        for attempt in range(3):
            response = self._request("GET", path, params=params)
            if response.status_code in (429, 503) and attempt < 2:
                sleep(self._retry_delay(response, attempt))
                continue
            response.raise_for_status()
            return response.json()

    def ticket(self, ticket_id: str) -> dict:
        return self._get(f"/tickets/{ticket_id}")

    def status(self) -> dict:
        return self._get("/status")

    def examples(self) -> list[dict]:
        return self._get("/examples")["examples"]

    def reset(self) -> dict:
        response = self._request("POST", "/practice/reset")
        response.raise_for_status()
        return response.json() if response.content else {}

    def tickets(self, status: str = "open") -> list[dict]:
        tickets = []
        cursor = None
        while True:
            params = {"limit": 10, "status": status}
            if cursor is not None:
                params["cursor"] = cursor
            page = self._get("/tickets", **params)
            tickets.extend(page["tickets"])
            cursor = page.get("next_cursor")
            if cursor is None:
                return tickets

    def post_action(self, ticket_id: str, action: Action, body: PostBody) -> str:
        handled = self.ticket(ticket_id).get("handled", "unknown")
        if handled is True or isinstance(handled, dict) and handled:
            return "already_handled"
        if handled is not False and handled is not None:
            return "uncertain"

        path = f"/tickets/{ticket_id}/{action}"
        payload = body.model_dump(exclude_none=True)
        for attempt in range(3):
            try:
                response = self._request("POST", path, json=payload)
            except httpx.TransportError:
                # A lost response does not mean the server lost the write.
                try:
                    handled = self.ticket(ticket_id).get("handled", "unknown")
                except (httpx.HTTPError, ValueError, AttributeError):
                    return "uncertain"
                if handled is True or isinstance(handled, dict) and handled:
                    return "already_handled"
                if (handled is not False and handled is not None) or attempt == 2:
                    return "uncertain"
                continue
            if response.status_code == 409:
                return "already_handled"
            if response.status_code in (429, 503) and attempt < 2:
                sleep(self._retry_delay(response, attempt))
                continue
            response.raise_for_status()
            return "delivered"

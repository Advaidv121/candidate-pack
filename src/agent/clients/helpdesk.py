import httpx


class HelpdeskClient:
    """Read status, examples, and tickets from the API."""

    def __init__(self, client: httpx.Client):
        self.client = client

    def _get(self, path: str, **params) -> dict:
        response = self.client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    def status(self) -> dict:
        return self._get("/status")

    def examples(self) -> list[dict]:
        return self._get("/examples")["examples"]

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

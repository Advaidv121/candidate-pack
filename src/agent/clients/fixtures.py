import json
from pathlib import Path


class FixtureHelpdeskClient:
    """Read captured data without credentials or network requests."""

    def __init__(self, directory: Path):
        self.directory = directory

    def _read(self, filename: str):
        return json.loads((self.directory / filename).read_text(encoding="utf-8"))

    def status(self) -> dict:
        return self._read("status.json")

    def examples(self) -> list[dict]:
        return self._read("examples.json")["examples"]

    def tickets(self, status: str = "open") -> list[dict]:
        tickets = self._read("tickets.json")
        return tickets if status == "all" else [t for t in tickets if not t.get("handled", False)]


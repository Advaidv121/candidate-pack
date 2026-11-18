"""Record simulated actions locally; never call the helpdesk API."""
import json
from pathlib import Path

from agent.clients.fixtures import FixtureHelpdeskClient


class LocalHelpdeskClient(FixtureHelpdeskClient):
    def __init__(self, directory: Path, outcomes_path: Path):
        super().__init__(directory)
        self.outcomes_path = outcomes_path
        self.outcomes = json.loads(outcomes_path.read_text()) if outcomes_path.exists() else {}

    def handled(self, ticket: dict) -> bool:
        return bool(ticket.get("handled")) or ticket["id"] in self.outcomes

    def record(self, ticket_id: str, action: str, body: dict) -> str:
        if ticket_id in self.outcomes:
            return "skipped"
        self.outcomes[ticket_id] = {"action": action, "body": body}
        self.outcomes_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.outcomes_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.outcomes, ensure_ascii=False, indent=2))
        temporary.replace(self.outcomes_path)
        return "simulated"

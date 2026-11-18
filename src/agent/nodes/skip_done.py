"""Check fixture status and previously simulated outcomes."""
from agent.clients.fake_helpdesk import FakeHelpdeskClient
from agent.state import TicketState


def skip_done(state: TicketState, client: FakeHelpdeskClient) -> dict:
    return {"outcome": "skipped" if client.handled(state["ticket"]) else "pending"}

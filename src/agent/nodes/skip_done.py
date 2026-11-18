"""Check fixture status and previously simulated outcomes."""
from agent.clients.local_helpdesk import LocalHelpdeskClient
from agent.state import TicketState


def skip_done(state: TicketState, client) -> dict:
    ticket = state["ticket"]
    handled = client.handled(ticket) if isinstance(client, LocalHelpdeskClient) else ticket.get("handled")
    return {"outcome": "skipped" if handled else "pending"}

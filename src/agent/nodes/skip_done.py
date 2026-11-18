"""Check if ticket was already handled."""
from agent.state import TicketState


def skip_done(state: TicketState, client=None) -> dict:
    ticket = state["ticket"]
    handled = ticket.get("handled")
    return {"outcome": "skipped" if handled else "pending"}

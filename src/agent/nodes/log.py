"""Log outcomes, scores, and sanitized input/decision without payment details."""
import json
from datetime import datetime, timezone
from pathlib import Path

from agent.redaction import redact
from agent.state import TicketState


def log(state: TicketState, path: Path) -> dict:
    ticket = state.get("ticket") or {}
    ticket_id = ticket.get("id") if isinstance(ticket, dict) else getattr(ticket, "id", None)

    entry = {
        "time": datetime.now(timezone.utc).isoformat(),
        "ticket_id": ticket_id,
        "outcome": state.get("outcome"),
    }

    if state.get("decision"):
        decision = state["decision"]
        entry["action"] = decision.action if hasattr(decision, "action") else decision.get("action")

        # Log sanitized input
        if state.get("model_ticket"):
            input_ticket = dict(state["model_ticket"])
        elif isinstance(ticket, dict):
            input_ticket = {k: ticket[k] for k in ("subject", "body", "customer_plan") if k in ticket}
        else:
            input_ticket = {}

        # Include channel if present
        channel = ticket.get("channel") if isinstance(ticket, dict) else getattr(ticket, "channel", None)
        if channel:
            input_ticket["channel"] = channel

        entry["input"] = redact(input_ticket)

        # Log sanitized decision
        dec_dict = decision.model_dump() if hasattr(decision, "model_dump") else dict(decision)
        entry["decision"] = redact(dec_dict)

    for key in ("confidence", "scores", "usage", "error", "score_error"):
        if key in state and state[key] is not None:
            entry[key] = state[key]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return {}


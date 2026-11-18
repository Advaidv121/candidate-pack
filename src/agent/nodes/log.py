"""Log outcomes and scores, without ticket text or generated messages."""
import json
from datetime import datetime, timezone
from pathlib import Path

from agent.state import TicketState


def log(state: TicketState, path: Path) -> dict:
    entry = {"time": datetime.now(timezone.utc).isoformat(),
             "ticket_id": state["ticket"]["id"], "outcome": state["outcome"]}
    if state.get("decision"):
        entry["action"] = state["decision"].action
    for key in ("scores", "usage", "error", "score_error"):
        if key in state:
            entry[key] = state[key]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(entry) + "\n")
    return {}

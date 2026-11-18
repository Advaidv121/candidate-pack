"""Send the validated decision through the selected helpdesk client."""
import re

from agent.clients.helpdesk import HelpdeskClient
from agent.schemas import PostBody
from agent.state import TicketState


def deliver(state: TicketState, client) -> dict:
    # The action belongs in the endpoint URL, not in the request body.
    fields = state["decision"].model_dump(exclude={"action"})
    fields["confidence"] = state.get("confidence")
    body = PostBody.model_validate(fields)
    if isinstance(client, HelpdeskClient):
        payment = r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)|\b[A-Z]{2} ?\d{2}(?: ?[A-Z0-9]){11,30}\b"
        if any(re.search(payment, value or "", re.I) for value in (body.reason, body.draft_reply, body.handoff_note)):
            return {"outcome": "error", "error": "PaymentDetailsDetected"}
        return {"outcome": client.post_action(state["ticket"]["id"], state["decision"].action, body)}
    body = body.model_dump(exclude_none=True)
    return {"outcome": client.record(state["ticket"]["id"],
                                     state["decision"].action, body)}

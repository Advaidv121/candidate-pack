"""Send the validated decision through the helpdesk client."""
from agent.redaction import contains_payment_details
from agent.schemas import PostBody
from agent.state import TicketState


def deliver(state: TicketState, client) -> dict:
    # The action belongs in the endpoint URL, not in the request body.
    fields = state["decision"].model_dump(exclude={"action"})
    fields["confidence"] = state.get("confidence")
    body = PostBody.model_validate(fields)

    if any(contains_payment_details(value) for value in (body.reason, body.draft_reply, body.handoff_note)):
        return {"outcome": "error", "error": "PaymentDetailsDetected"}
    return {"outcome": client.post_action(state["ticket"]["id"], state["decision"].action, body)}

"""Call the model and return a validated decision."""

import re

from agent.clients.llm import build_messages, generate
from agent.config import Settings
from agent.schemas import LLMDecision, TicketInput
from agent.state import TicketState


def protect(value):
    if not isinstance(value, str):
        return value
    return re.sub(r"(?<!\d)(?:\d[\s-]?){12,18}\d(?!\d)|\b[A-Z]{2}\s?\d{2}(?:\s?[A-Z0-9]){11,30}\b",
                  "[payment detail removed]", value, flags=re.I)


def decide(state: TicketState, settings: Settings) -> dict:
    ticket_in = TicketInput.model_validate(state["ticket"])
    # Send only the fields the model needs; raw metadata stays local.
    ticket = ticket_in.to_model_ticket().model_dump()
    ticket = {k: protect(v) for k, v in ticket.items()}
    decision, token_usage = generate(build_messages(ticket), settings)
    # Mask echoed payment details before scoring or delivery.
    decision = LLMDecision.model_validate({k: protect(v) for k, v in decision.model_dump().items()})
    usage = {"prompt_tokens": token_usage.get("input_tokens", 0),
             "completion_tokens": token_usage.get("output_tokens", 0),
             "total_tokens": token_usage.get("total_tokens", 0)}
    return {"model_ticket": ticket, "decision": decision, "usage": usage}

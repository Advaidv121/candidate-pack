"""Call the model and return a validated decision."""

import re

from agent.clients.llm import build_messages, generate
from agent.config import Settings
from agent.schemas import LLMDecision
from agent.state import TicketState


def protect(value):
    if not isinstance(value, str):
        return value
    return re.sub(r"(?<!\d)(?:\d[\s-]?){12,18}\d(?!\d)|\b[A-Z]{2}\s?\d{2}(?:\s?[A-Z0-9]){11,30}\b",
                  "[payment detail removed]", value, flags=re.I)


def decide(state: TicketState, settings: Settings) -> dict:
    # Send only the fields the model needs; raw metadata stays local.
    ticket = {key: state["ticket"][key]
              for key in ("id", "subject", "body", "customer_plan")}
    ticket = {k: protect(v) for k, v in ticket.items()}
    response = generate(build_messages(ticket), settings)
    decision = LLMDecision.model_validate_json(response.choices[0].message.content or "")
    # Mask echoed payment details before scoring or delivery.
    decision = LLMDecision.model_validate({k: protect(v) for k, v in decision.model_dump().items()})
    usage = {key: getattr(response.usage, key, 0) or 0
             for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
    return {"model_ticket": ticket, "decision": decision, "usage": usage}

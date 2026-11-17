"""Call Gemini and return a validated decision."""

from agent.clients.llm import build_messages, generate
from agent.config import Settings
from agent.schemas import LLMDecision
from agent.state import TicketState


def draft(state: TicketState, settings: Settings) -> dict:
    ticket = {key: state["ticket"][key]
              for key in ("id", "subject", "body", "customer_plan")}
    response = generate(build_messages(ticket), settings)
    decision = LLMDecision.model_validate_json(response.choices[0].message.content or "")
    usage = {key: getattr(response.usage, key, 0) or 0
             for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
    return {"model_ticket": ticket, "decision": decision, "usage": usage}

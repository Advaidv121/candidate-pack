"""Add confidence without changing the LLM's decision."""
from agent.clients.jev import evaluate
from agent.config import Settings
from agent.state import TicketState


def score(state: TicketState, settings: Settings) -> dict:
    scores = evaluate(state["model_ticket"], state["decision"], settings)
    # Published confidence measures action fit; other scores are diagnostic.
    return {"confidence": scores["action"], "scores": scores}

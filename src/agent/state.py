"""LangGraph state for one ticket."""
from typing import TypedDict

from .schemas import LLMDecision, TicketInput


class TicketState(TypedDict, total=False):
    ticket: TicketInput | dict  # raw ticket from the API
    model_ticket: dict         # selected fields sent to the model
    decision: LLMDecision      # structured output from the LLM
    usage: dict                # token counts from the model call
    confidence: float          # Jev's probability the action fits the policy
    scores: dict               # separate Jev checks for inspection
    outcome: str               # pending | delivered | skipped | error | already_handled | uncertain
    error: str                 # exception type only
    score_error: str

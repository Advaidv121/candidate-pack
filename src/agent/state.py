"""LangGraph state for one ticket."""
from typing import TypedDict

from .schemas import LLMDecision


class TicketState(TypedDict, total=False):
    ticket: dict              # raw ticket from the API
    model_ticket: dict        # selected fields sent to the model
    decision: LLMDecision     # structured output from the LLM
    usage: dict               # token counts from the model call

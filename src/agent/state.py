"""LangGraph state for one ticket."""
from typing import Optional, TypedDict

from .schemas import LLMDecision


class TicketState(TypedDict, total=False):
    ticket: dict              # raw ticket from the API
    skip: bool                # already handled -> only log
    redacted_body: str        # body with IBANs/cards masked, sent to LLM and logs
    decision: LLMDecision     # structured output from the LLM
    forced_handoff: bool      # LLM output stayed invalid after one retry
    confidence: Optional[float]  # from Jev; informational only
    outcome: str              # posted | skipped | already_handled | error

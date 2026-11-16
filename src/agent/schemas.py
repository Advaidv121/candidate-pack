"""Contracts. The LLM produces the full decision; Jev only adds `confidence`."""
from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator

Action = Literal["reply", "handoff", "close"]
Language = Literal["nl", "en", "de"]
Category = Literal["bug", "billing", "feature_request", "question", "other"]
Priority = Literal["P1", "P2", "P3", "P4"]


class LLMDecision(BaseModel):
    """Structured output requested from the LLM (also the eval's unit of comparison)."""
    action: Action
    language: Language
    category: Category
    priority: Priority
    reason: str = Field(min_length=1, description="1-2 sentences: why this category, priority and action")
    draft_reply: Optional[str] = Field(None, description="Answer in the customer's language; only for reply")
    handoff_note: Optional[str] = Field(None, description="English note for the support agent; only for handoff")

    @model_validator(mode="after")
    def _payload_matches_action(self):
        if self.action == "reply" and not self.draft_reply:
            raise ValueError("reply needs draft_reply")
        if self.action == "handoff" and not self.handoff_note:
            raise ValueError("handoff needs handoff_note")
        return self


class PostBody(BaseModel):
    """Body sent to /reply, /handoff or /close. Confidence comes from Jev and decides nothing."""
    language: Language
    category: Category
    priority: Priority
    reason: str
    draft_reply: Optional[str] = None
    handoff_note: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0, le=1)

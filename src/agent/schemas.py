"""Contracts. The LLM produces the full decision; Jev only adds `confidence`."""
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

Action = Literal["reply", "handoff", "close"]
Language = Literal["nl", "en", "de"]
Category = Literal["bug", "billing", "feature_request", "question", "other"]
Priority = Literal["P1", "P2", "P3", "P4"]


class LLMDecision(BaseModel):
    """Structured output requested from the LLM (also the eval's unit of comparison)."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    action: Action
    language: Language
    category: Category
    priority: Priority
    reason: str = Field(min_length=1, description="1-2 sentences: why this category, priority and action")
    draft_reply: Optional[str] = Field(..., min_length=1, description="Answer in the customer's language; null unless reply")
    handoff_note: Optional[str] = Field(..., min_length=1, description="English note for the support agent; null unless handoff")

    @model_validator(mode="after")
    def _payload_matches_action(self):
        if self.action == "reply" and not self.draft_reply:
            raise ValueError("reply needs draft_reply")
        if self.action == "handoff" and not self.handoff_note:
            raise ValueError("handoff needs handoff_note")
        if self.action != "reply" and self.draft_reply is not None:
            raise ValueError("draft_reply must be null unless reply")
        if self.action != "handoff" and self.handoff_note is not None:
            raise ValueError("handoff_note must be null unless handoff")
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

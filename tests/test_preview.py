import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from agent.config import Settings
from agent.graph import build_preview_graph
from agent.schemas import LLMDecision


SETTINGS = Settings("", "", "", "", "gemini/gemini-3.1-flash-lite",
                    {"llm": {"temperature": 0}})
TICKET = {"id": "T1", "subject": "Payment",
          "body": "Card 4111 1111 1111 1111, CVC 123, geldig tot 09/28",
          "customer_plan": "Basis", "label": {"action": "reply"}}
DECISION = dict(action="handoff", language="en", category="billing", priority="P2",
                reason="Payment request needs a human.", draft_reply=None,
                handoff_note="Please review the payment request.")


def response(content):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=100, completion_tokens=20, total_tokens=120))


def test_preview_sends_schema_and_excludes_labels(monkeypatch):
    def complete(**kwargs):
        assert kwargs["response_format"] is LLMDecision
        assert kwargs["model"] == SETTINGS.gemini_model
        ticket = json.loads(kwargs["messages"][1]["content"])["ticket"]
        assert set(ticket) == {"id", "subject", "body", "customer_plan"}
        assert ticket["body"] == TICKET["body"]
        assert "F02" in kwargs["messages"][0]["content"]
        return response(json.dumps(DECISION))

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr("agent.clients.llm.completion", complete)
    result = build_preview_graph(SETTINGS).invoke({"ticket": TICKET})
    assert result["decision"].action == "handoff"


def test_invalid_output_reports_validation_error(monkeypatch):
    calls = []

    def generate(messages, settings):
        calls.append(len(messages))
        return response("invalid JSON")

    monkeypatch.setattr("agent.nodes.draft.generate", generate)
    with pytest.raises(ValidationError):
        build_preview_graph(SETTINGS).invoke({"ticket": TICKET})
    assert calls == [2]


@pytest.mark.parametrize("changes", [
    {"draft_reply": "Cannot reply and hand off"},
    {"handoff_note": "   "},
    {"confidence": 0.9},
])
def test_schema_rejects_invalid_action_fields_and_llm_confidence(changes):
    with pytest.raises(ValidationError):
        LLMDecision.model_validate({**DECISION, **changes})

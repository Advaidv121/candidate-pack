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
        assert kwargs["model"] == SETTINGS.llm_model
        ticket = json.loads(kwargs["messages"][1]["content"])["ticket"]
        assert set(ticket) == {"id", "subject", "body", "customer_plan"}
        assert "4111" not in ticket["body"]
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


def test_fal_uses_router_key_and_structured_output(monkeypatch):
    settings = Settings("", "", "", "", "openai/deepseek/deepseek-v4.1-flash",
                        {"llm": {"temperature": 0,
                                 "api_base": "https://fal.run/openrouter/router/openai/v1"}})

    def complete(**kwargs):
        assert kwargs["model"] == settings.llm_model
        assert kwargs["api_base"] == settings.raw["llm"]["api_base"]
        assert kwargs["extra_headers"] == {"Authorization": "Key test-fal-key"}
        assert kwargs["response_format"] is LLMDecision
        return response(json.dumps(DECISION))

    monkeypatch.setenv("FAL_KEY", "test-fal-key")
    monkeypatch.setattr("agent.clients.llm.completion", complete)
    result = build_preview_graph(settings).invoke({"ticket": TICKET})
    assert result["decision"].action == "handoff"


def test_jev_uses_litellm_and_only_adds_score(monkeypatch):
    settings = Settings("", "", "", "", SETTINGS.llm_model,
                        {"llm": {"temperature": 0},
                         "jev": {"model": "typesafe/jev-1.14.0"}})

    def systemone(**kwargs):
        assert kwargs["model"] == "typesafe/jev-1.14.0"
        assert kwargs["api_key"] == "test-jev-key"
        assert kwargs["state"]["decision"] == DECISION
        assert "label" not in kwargs["state"]["ticket"]
        assert set(kwargs["questions"]) == {"action", "language", "category", "priority", "grounding"}
        return SimpleNamespace(answers={name: SimpleNamespace(noul=0.12)
                                        for name in kwargs["questions"]})

    monkeypatch.setenv("JEV_API_KEY", "test-jev-key")
    monkeypatch.setattr("agent.nodes.draft.generate", lambda *args: response(json.dumps(DECISION)))
    monkeypatch.setattr("agent.clients.jev.systemone", systemone)
    result = build_preview_graph(settings, with_score=True).invoke({"ticket": TICKET})
    assert result["confidence"] == 0.12
    assert result["decision"].model_dump() == DECISION


def test_jev_failure_is_an_error_not_a_score(monkeypatch):
    def fail(*args):
        raise RuntimeError("Scoring unavailable")

    monkeypatch.setattr("agent.nodes.draft.generate", lambda *args: response(json.dumps(DECISION)))
    monkeypatch.setattr("agent.nodes.score.evaluate", fail)
    with pytest.raises(RuntimeError, match="Scoring unavailable"):
        build_preview_graph(SETTINGS, with_score=True).invoke({"ticket": TICKET})


@pytest.mark.parametrize("changes", [
    {"draft_reply": "Cannot reply and hand off"},
    {"handoff_note": "   "},
    {"confidence": 0.9},
])
def test_schema_rejects_invalid_action_fields_and_llm_confidence(changes):
    with pytest.raises(ValidationError):
        LLMDecision.model_validate({**DECISION, **changes})

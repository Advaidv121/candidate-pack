from types import SimpleNamespace

import pytest
import yaml

from agent.clients.jev import evaluate
from agent.config import ROOT, Settings
from agent.schemas import LLMDecision


def test_language_question_checks_reply_text_not_only_metadata():
    question = yaml.safe_load((ROOT / "config/jev_questions.yaml").read_text())["language"]

    assert "decision.draft_reply" in question["instructions"]
    assert "decision.language" in question["instructions"]
    assert "customer" in question["instructions"]
    assert "substantive explanatory sentence" in question["criteria"]["true"]
    assert "UI labels" in question["criteria"]["true"]
    assert "handoff_note" in question["criteria"]["true"]
    assert "matching language label" in question["criteria"]["false"]


@pytest.mark.parametrize("reply", [
    "Open de dienst en tik op Ruil aanbieden.",
    "Open the shift and tap Ruil aanbieden.",
])
def test_jev_receives_actual_reply_and_language_criteria(reply, monkeypatch):
    ticket = {"id": "T005", "subject": "Dienst ruilen", "body": "Hoe ruil ik mijn dienst?"}
    decision = LLMDecision(
        action="reply", language="nl", category="question", priority="P4",
        reason="FAQ covers shift swaps.", draft_reply=reply, handoff_note=None,
    )
    settings = Settings("", "", "", "", "test", {"jev": {"model": "jev-1.14.0"}})

    def system_one(self, **kwargs):
        assert kwargs["state"]["ticket"] == ticket
        assert kwargs["state"]["decision"]["draft_reply"] == reply
        assert kwargs["state"]["decision"]["language"] == "nl"
        language = kwargs["questions"]["language"]
        assert "decision.draft_reply" in language.instructions
        assert "matching language label" in language.criteria["false"]
        # The mock verifies wiring, not Jev's semantic language accuracy.
        return SimpleNamespace(answers={
            name: SimpleNamespace(noul=0.5) for name in kwargs["questions"]
        })

    monkeypatch.setenv("JEV_API_KEY", "test-key")
    monkeypatch.setattr("agent.clients.jev.TypeSafeClient.system_one", system_one)

    assert evaluate(ticket, decision, settings)["language"] == 0.5

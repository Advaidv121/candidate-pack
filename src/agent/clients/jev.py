"""Score an existing decision through LiteLLM's TypeSafe integration."""
import os

import yaml
from litellm import systemone

from agent.config import ROOT, Settings
from agent.schemas import LLMDecision


def evaluate(ticket: dict, decision: LLMDecision, settings: Settings) -> dict[str, float]:
    key = os.getenv("JEV_API_KEY") or os.getenv("TYPESAFE_API_KEY")
    if not key:
        raise RuntimeError("Missing JEV_API_KEY (or TYPESAFE_API_KEY)")
    questions = yaml.safe_load((ROOT / "config/jev_questions.yaml").read_text())
    response = systemone(
        model=settings.raw["jev"]["model"],
        api_key=key,
        state={
            "ticket": ticket,
            "decision": decision.model_dump(),
            "policy": (ROOT / "prompts/system.md").read_text(),
            "faq": (ROOT / "knowledge/faq.md").read_text(),
        },
        questions=questions,
        timeout=30,
    )
    # Noul is P(yes), not the separate certainty metric on Choice/Score answers.
    scores = {name: response.answers[name].noul for name in questions}
    if any(not 0 <= value <= 1 for value in scores.values()):
        raise ValueError("Jev returned a probability outside [0, 1]")
    return scores

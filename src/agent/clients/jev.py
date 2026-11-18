"""Score an existing decision directly through TypeSafe."""
import os

import yaml
from typesafe_sdk import Noul, TypeSafeClient

from agent.config import ROOT, Settings
from agent.schemas import LLMDecision


def evaluate(ticket: dict, decision: LLMDecision, settings: Settings) -> dict[str, float]:
    key = os.getenv("JEV_API_KEY") or os.getenv("TYPESAFE_API_KEY")
    if not key:
        raise RuntimeError("Missing JEV_API_KEY (or TYPESAFE_API_KEY)")
    questions = {name: Noul(**question) for name, question in
                 yaml.safe_load((ROOT / "config/jev_questions.yaml").read_text()).items()}
    with TypeSafeClient(api_key=key, timeout=30) as client:
        response = client.system_one(
            model=settings.raw["jev"]["model"],
            state={
                "ticket": ticket,
                "decision": decision.model_dump(),
                "policy": (ROOT / "prompts/system.md").read_text(),
                "faq": (ROOT / "knowledge/faq.md").read_text(),
            },
            questions=questions,
        )
    # Noul is P(yes), not the separate certainty metric on Choice/Score answers.
    scores = {name: response.answers[name].noul for name in questions}
    if any(not 0 <= value <= 1 for value in scores.values()):
        raise ValueError("Jev returned a probability outside [0, 1]")
    return scores

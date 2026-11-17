"""The only Gemini call: LiteLLM with a Pydantic response schema."""
import json
import os

from litellm import completion

from agent.config import ROOT, Settings
from agent.schemas import LLMDecision


def build_messages(ticket: dict) -> list[dict]:
    prompt = (ROOT / "prompts/system.md").read_text(encoding="utf-8")
    faq = (ROOT / "knowledge/faq.md").read_text(encoding="utf-8")
    return [
        {"role": "system", "content": prompt + "\n\n" + faq},
        {"role": "user", "content": json.dumps({"ticket": ticket}, ensure_ascii=False)},
    ]


def generate(messages: list[dict], settings: Settings):
    if not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError("Missing GEMINI_API_KEY")
    return completion(
        model=settings.gemini_model,
        api_key=os.environ["GEMINI_API_KEY"],
        messages=messages,
        response_format=LLMDecision,
        temperature=settings.raw["llm"]["temperature"],
        timeout=60,
        num_retries=0,
    )

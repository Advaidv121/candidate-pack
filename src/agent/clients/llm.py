"""LiteLLM structured output; default is DeepSeek through fal.ai."""
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
    if settings.llm_model.startswith("gemini/"):
        key_name = "GEMINI_API_KEY"
        connection = {"api_key": os.getenv(key_name)}
    else:
        key_name = "FAL_KEY"
        connection = {
            "api_key": "not-needed",
            "api_base": settings.raw["llm"]["api_base"],
            "extra_headers": {"Authorization": f"Key {os.getenv(key_name, '')}"},
        }
    if not os.getenv(key_name):
        raise RuntimeError(f"Missing {key_name}")
    return completion(
        model=settings.llm_model,
        **connection,
        messages=messages,
        response_format=LLMDecision,
        temperature=settings.raw["llm"]["temperature"],
        timeout=60,
        num_retries=0,
    )

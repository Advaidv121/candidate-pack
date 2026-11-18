"""LiteLLM structured output; default is DeepSeek through fal.ai."""
import json
import os

from langchain_litellm import ChatLiteLLM

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
        api_key = os.getenv(key_name)
        api_base = None
        extra_headers = None
    else:
        key_name = "FAL_KEY"
        api_key = "not-needed"
        api_base = settings.raw["llm"]["api_base"]
        extra_headers = {"Authorization": f"Key {os.getenv(key_name, '')}"}
    if not os.getenv(key_name):
        raise RuntimeError(f"Missing {key_name}")
    model = ChatLiteLLM(
        model=settings.llm_model,
        api_key=api_key,
        api_base=api_base,
        extra_headers=extra_headers,
        temperature=settings.raw["llm"]["temperature"],
        request_timeout=60,
        max_retries=0,
        model_kwargs={"num_retries": 0},
    )
    result = model.with_structured_output(LLMDecision, include_raw=True).invoke(messages)
    if result["parsing_error"] is not None:
        raise result["parsing_error"]
    if result["parsed"] is None:
        raise ValueError("Model did not return a ticket decision")
    return result["parsed"], result["raw"].usage_metadata or {}

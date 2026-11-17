"""Loads .env and config/settings.yaml into one immutable Settings object."""
import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    base_url: str
    api_key: str
    email: str
    name: str
    llm_model: str
    raw: dict

    def headers(self) -> dict:
        h = {"Authorization": f"Bearer {self.api_key}", "X-Candidate-Email": self.email}
        if self.name:
            h["X-Candidate-Name"] = self.name
        return h


def load_settings() -> Settings:
    load_dotenv(ROOT / ".env")
    raw = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text())
    missing = [k for k in ("HELPDESK_API_KEY", "HELPDESK_EMAIL", "HELPDESK_BASE_URL") if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing env vars: {', '.join(missing)}")
    return Settings(
        base_url=os.environ["HELPDESK_BASE_URL"].rstrip("/"),
        api_key=os.environ["HELPDESK_API_KEY"],
        email=os.environ["HELPDESK_EMAIL"],
        name=os.getenv("HELPDESK_CANDIDATE_NAME", ""),
        llm_model=os.getenv("LLM_MODEL", raw["llm"]["model"]),
        raw=raw,
    )

"""Explicitly refresh saved fixtures using the reusable live reader."""
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from agent.clients.helpdesk import HelpdeskClient
from agent.config import ROOT, load_settings


def main():
    settings = load_settings()
    output = ROOT / "fixtures"
    output.mkdir(exist_ok=True)
    with httpx.Client(base_url=settings.base_url, headers=settings.headers(),
                      timeout=settings.raw["helpdesk"]["timeout_s"]) as transport:
        client = HelpdeskClient(transport)
        snapshot = {
            "status.json": client.status(),
            "examples.json": {"examples": client.examples()},
            "tickets.json": client.tickets(status="all"),
        }
    for filename, data in snapshot.items():
        (output / filename).write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {len(snapshot['tickets.json'])} tickets and "
          f"{len(snapshot['examples.json']['examples'])} labelled examples.")


if __name__ == "__main__":
    main()

"""Read saved tickets by default; --source live performs read-only API calls."""
import argparse
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from agent.clients.fixtures import FixtureHelpdeskClient
from agent.clients.helpdesk import HelpdeskClient
from agent.config import ROOT, load_settings


def summarize(source):
    tickets = source.tickets(status="all")
    examples = source.examples()
    print(f"Practice tickets: {len(tickets)}")
    print(f"Open tickets: {sum(not t.get('handled', False) for t in tickets)}")
    print(f"Labelled evaluation cases: {len(examples)}")
    print("Ticket IDs: " + ", ".join(t["id"] for t in tickets))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("fixtures", "live"), default="fixtures")
    args = parser.parse_args()
    if args.source == "fixtures":
        summarize(FixtureHelpdeskClient(ROOT / "fixtures"))
    else:
        settings = load_settings()
        with httpx.Client(base_url=settings.base_url, headers=settings.headers(),
                          timeout=settings.raw["helpdesk"]["timeout_s"]) as transport:
            summarize(HelpdeskClient(transport))


if __name__ == "__main__":
    main()

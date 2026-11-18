"""Deliver decisions to the helpdesk."""
import argparse
import json
from pathlib import Path

import httpx

from agent.clients.helpdesk import HelpdeskClient
from agent.config import ROOT, Settings, load_settings
from agent.graph import build_delivery_graph
from agent.nodes.log import log


def run_tickets(settings: Settings, client: HelpdeskClient, log_path: Path,
                ticket_ids: list[str] | None = None, with_score: bool = False) -> dict:
    tickets = client.tickets(status="open")
    if ticket_ids:
        tickets = [ticket for ticket in tickets if ticket["id"] in ticket_ids]
    graph = build_delivery_graph(settings, client, log_path, with_score)
    counts = {"delivered": 0, "already_handled": 0, "uncertain": 0, "skipped": 0, "error": 0}
    if not tickets:
        print("No open tickets matched the requested IDs." if ticket_ids
              else "No open tickets to process.", flush=True)
    for ticket in tickets:
        try:
            state = graph.invoke({"ticket": ticket})
        except Exception as error:
            state = {"ticket": ticket, "outcome": "error", "error": type(error).__name__}
            log(state, log_path)
        counts[state["outcome"]] += 1
        print(ticket["id"], state["outcome"], state.get("error", ""), flush=True)
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids", nargs="+", help="Only these ticket IDs")
    parser.add_argument("--score", action="store_true", help="Call Jev after generation")
    parser.add_argument("--reset", action="store_true", help="Reset tickets and exit")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    settings = load_settings()
    output = args.output_dir or ROOT / "logs/live"
    with httpx.Client(base_url=settings.base_url, headers=settings.headers(),
                      timeout=settings.raw["helpdesk"]["timeout_s"]) as transport:
        client = HelpdeskClient(transport)
        if args.reset:
            client.reset()
            print("Reset tickets successfully.")
            status = client.status()
            print(json.dumps({"server": {key: status[key] for key in
                                          ("open_tickets", "handled_tickets")}}, indent=2))
            return
        counts = run_tickets(settings, client, output / "run.jsonl", args.ids, args.score)
        status = client.status()
    print(json.dumps({
        "server": {key: status[key] for key in ("open_tickets", "handled_tickets")},
        "run": {"processed": sum(counts.values()), **counts},
    }, indent=2))
    if counts["error"] or counts.get("uncertain"):
        raise SystemExit(1)

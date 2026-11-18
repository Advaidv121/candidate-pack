"""Run saved tickets through a local helpdesk simulation."""
import argparse
from pathlib import Path

from agent.clients.fake_helpdesk import FakeHelpdeskClient
from agent.config import ROOT, Settings, load_settings
from agent.graph import build_simulation_graph
from agent.nodes.log import log


def run_simulation(settings: Settings, client: FakeHelpdeskClient, log_path: Path,
                   ticket_ids: list[str] | None = None, with_score: bool = False) -> dict:
    tickets = client.tickets(status="all")
    if ticket_ids:
        unknown = set(ticket_ids) - {ticket["id"] for ticket in tickets}
        if unknown:
            raise ValueError("Unknown ticket IDs: " + ", ".join(sorted(unknown)))
        tickets = [ticket for ticket in tickets if ticket["id"] in ticket_ids]
    graph = build_simulation_graph(settings, client, log_path, with_score)
    counts = {"simulated": 0, "skipped": 0, "error": 0}
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
    parser.add_argument("--ids", nargs="+", help="Only these saved ticket IDs")
    parser.add_argument("--score", action="store_true", help="Call Jev after generation")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "logs/simulation")
    args = parser.parse_args()
    client = FakeHelpdeskClient(ROOT / "fixtures", args.output_dir / "outcomes.json")
    counts = run_simulation(load_settings(), client, args.output_dir / "run.jsonl",
                            args.ids, args.score)
    print(counts)
    if counts["error"]:
        raise SystemExit(1)

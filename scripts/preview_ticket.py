"""Generate a decision from a saved ticket; never post to the helpdesk."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from agent.clients.fixtures import FixtureHelpdeskClient
from agent.config import ROOT, load_settings
from agent.graph import build_preview_graph


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ticket_ids", nargs="+", help="Saved IDs, e.g. T005 T003 T011")
    args = parser.parse_args()
    source = FixtureHelpdeskClient(ROOT / "fixtures")
    tickets = {t["id"]: t for t in source.tickets(status="all")}
    unknown = set(args.ticket_ids) - tickets.keys()
    if unknown:
        parser.error("Unknown ticket IDs: " + ", ".join(sorted(unknown)))
    settings = load_settings()
    graph = build_preview_graph(settings)
    output_dir = ROOT / "logs/previews"
    output_dir.mkdir(parents=True, exist_ok=True)
    for ticket_id in args.ticket_ids:
        state = graph.invoke({"ticket": tickets[ticket_id]})
        preview = {
            "model": settings.llm_model,
            "input": {"ticket": state["model_ticket"]},
            "decision": state["decision"].model_dump(),
            "usage": state["usage"],
        }
        text = json.dumps(preview, ensure_ascii=False, indent=2)
        (output_dir / f"{ticket_id}.json").write_text(text, encoding="utf-8")
        print(ticket_id, state["decision"].action, state["decision"].language,
              state["decision"].category, state["decision"].priority)


if __name__ == "__main__":
    main()

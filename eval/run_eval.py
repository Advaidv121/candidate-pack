"""Run saved labelled examples through the preview graph; never post actions."""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from agent.clients.fixtures import FixtureHelpdeskClient
from agent.config import ROOT, load_settings
from agent.graph import build_preview_graph
from metrics import FIELDS, summarize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids", nargs="+", help="Run only these example IDs")
    args = parser.parse_args()
    settings = load_settings()
    graph = build_preview_graph(settings)
    examples = FixtureHelpdeskClient(ROOT / "fixtures").examples()
    if args.ids:
        unknown = set(args.ids) - {example["id"] for example in examples}
        if unknown:
            parser.error("Unknown example IDs: " + ", ".join(sorted(unknown)))
        examples = [example for example in examples if example["id"] in args.ids]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = ROOT / "eval/results" / stamp
    output.mkdir(parents=True)
    sources = ("prompts/system.md", "knowledge/faq.md",
               "src/agent/schemas.py", "fixtures/examples.json")
    report = {
        "model": settings.llm_model,
        "llm_settings": settings.raw["llm"],
        "started_at_utc": stamp,
        "source_hashes": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                          for path in sources},
        "results": [],
    }
    # Preserve the exact prompt and FAQ for before/after comparison.
    for path in sources[:2]:
        (output / Path(path).name).write_bytes((ROOT / path).read_bytes())
    for example in examples:
        # Strip labels before invoking the graph. Models never receive ground truth.
        ticket = {key: value for key, value in example.items() if key != "label"}
        row = {"id": ticket["id"], "expected": example["label"]}
        try:
            state = graph.invoke({"ticket": ticket})
            row.update(
                input=state["model_ticket"], prediction=state["decision"].model_dump(),
                usage=state["usage"],
            )
            row["mismatches"] = {field: {"expected": row["expected"][field],
                                                "actual": row["prediction"][field]}
                                 for field in FIELDS
                                 if row["expected"][field] != row["prediction"][field]}
            print(row["id"], "MATCH" if not row["mismatches"] else row["mismatches"], flush=True)
        except Exception as error:
            # Avoid persisting provider exception text that may contain request data.
            row["error"] = type(error).__name__
            print(row["id"], row["error"], flush=True)
        report["results"].append(row)
        report["summary"] = summarize(report["results"])
        report["usage"] = {key: sum(r.get("usage", {}).get(key, 0) for r in report["results"])
                           for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
        (output / "results.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    print("Saved:", output / "results.json")


if __name__ == "__main__":
    main()

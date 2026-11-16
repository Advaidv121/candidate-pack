"""One-off: fetch /status, /examples, /tickets (all pages) once and save to fixtures/."""
import json, sys
from pathlib import Path
import httpx
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from agent.config import load_settings, ROOT

s = load_settings()
out = ROOT / "fixtures"; out.mkdir(exist_ok=True)
with httpx.Client(base_url=s.base_url, headers=s.headers(), timeout=20) as c:
    def get(path, **p):
        r = c.get(path, params=p); print(path, p, r.status_code); r.raise_for_status(); return r.json()
    (out / "status.json").write_text(json.dumps(get("/status"), indent=2, ensure_ascii=False))
    (out / "examples.json").write_text(json.dumps(get("/examples"), indent=2, ensure_ascii=False))
    items, cur = [], None
    while True:
        d = get("/tickets", status="all", **({"cursor": cur} if cur else {}))
        items += d.get("tickets", d.get("items", []))
        cur = d.get("next_cursor")
        if not cur: break
    (out / "tickets.json").write_text(json.dumps(items, indent=2, ensure_ascii=False))
    print("tickets:", len(items))

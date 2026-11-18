import json
from unittest.mock import MagicMock

import httpx

from agent.clients.helpdesk import HelpdeskClient
from agent.config import ROOT, Settings
from agent.main import run_tickets
from agent.schemas import LLMDecision

SETTINGS = Settings("", "", "", "", "test", {})


def decision(action):
    return LLMDecision(action=action, language="nl", category="other", priority="P4",
                       reason="Test decision", draft_reply="Test reply" if action == "reply" else None,
                       handoff_note="Test note" if action == "handoff" else None)


def test_30_tickets_deliver_actions_and_rerun_skips(tmp_path, monkeypatch):
    log_path = tmp_path / "run.jsonl"
    raw_tickets = json.loads((ROOT / "fixtures/tickets.json").read_text())
    # Create mutable copy of tickets for mock server
    server_tickets = {t["id"]: dict(t) for t in raw_tickets}
    delivered_actions = {}

    client = HelpdeskClient(httpx.Client())

    def mock_tickets(status="open"):
        return [t for t in server_tickets.values() if not t.get("handled", False)]

    def mock_ticket(ticket_id):
        return server_tickets[ticket_id]

    def mock_post_action(ticket_id, action, body):
        if server_tickets[ticket_id].get("handled"):
            return "already_handled"
        server_tickets[ticket_id]["handled"] = True
        delivered_actions[ticket_id] = {"action": action, "body": body.model_dump(exclude_none=True)}
        return "delivered"

    monkeypatch.setattr(client, "tickets", mock_tickets)
    monkeypatch.setattr(client, "ticket", mock_ticket)
    monkeypatch.setattr(client, "post_action", mock_post_action)

    calls = []

    def decide(state, settings):
        calls.append(state["ticket"]["id"])
        action = ("reply", "handoff", "close")[len(calls) % 3]
        return {"decision": decision(action), "model_ticket": state["ticket"]}

    monkeypatch.setattr("agent.graph.decide", decide)
    monkeypatch.setattr("agent.nodes.score.evaluate", lambda *args: {"action": 0.01})

    first = run_tickets(SETTINGS, client, log_path, with_score=True)
    assert first == {"delivered": 30, "already_handled": 0, "uncertain": 0, "skipped": 0, "error": 0}
    assert len(delivered_actions) == 30
    assert {entry["action"] for entry in delivered_actions.values()} == {"reply", "handoff", "close"}

    for entry in delivered_actions.values():
        body = entry["body"]
        assert body["confidence"] == 0.01
        assert "action" not in body
        assert ("draft_reply" in body) == (entry["action"] == "reply")
        assert ("handoff_note" in body) == (entry["action"] == "handoff")

    # Second run: open tickets is empty
    def unexpected(*args, **kwargs):
        raise AssertionError("Already handled tickets must not call models")

    monkeypatch.setattr("agent.graph.decide", unexpected)
    second = run_tickets(SETTINGS, client, log_path)
    assert second == {"delivered": 0, "already_handled": 0, "uncertain": 0, "skipped": 0, "error": 0}

    entries = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert len(entries) == 30
    assert all("body" not in entry and "reason" not in entry for entry in entries)


def test_failure_logs_safe_error_and_continues(tmp_path, monkeypatch):
    def decide(state, settings):
        if state["ticket"]["id"] == "T003":
            raise RuntimeError("Private provider request contents")
        return {"decision": decision("reply")}

    monkeypatch.setattr("agent.graph.decide", decide)

    client = HelpdeskClient(httpx.Client())
    monkeypatch.setattr(client, "tickets", lambda status="open": [
        {"id": "T003", "subject": "A", "body": "B", "customer_plan": "C"},
        {"id": "T005", "subject": "D", "body": "E", "customer_plan": "F"},
    ])
    monkeypatch.setattr(client, "post_action", lambda ticket_id, action, body: "delivered")

    log_path = tmp_path / "run.jsonl"
    result = run_tickets(SETTINGS, client, log_path, ["T003", "T005"])
    assert result == {"delivered": 1, "already_handled": 0, "uncertain": 0, "skipped": 0, "error": 1}
    assert "Private" not in log_path.read_text()
    assert len(log_path.read_text().splitlines()) == 2


def test_helpdesk_client_reset(monkeypatch):
    called = []

    def mock_request(self, method, path, **kwargs):
        called.append((method, path))
        req = httpx.Request(method, f"http://test{path}")
        return httpx.Response(200, json={"status": "reset"}, request=req)

    monkeypatch.setattr(HelpdeskClient, "_request", mock_request)
    client = HelpdeskClient(httpx.Client())
    res = client.reset()
    assert res == {"status": "reset"}
    assert called == [("POST", "/practice/reset")]

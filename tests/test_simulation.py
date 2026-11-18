import json

from agent.clients.local_helpdesk import LocalHelpdeskClient
from agent.config import ROOT, Settings
from agent.main import run_tickets
from agent.schemas import LLMDecision

SETTINGS = Settings("", "", "", "", "test", {})


def decision(action):
    return LLMDecision(action=action, language="nl", category="other", priority="P4",
                       reason="Test decision", draft_reply="Test reply" if action == "reply" else None,
                       handoff_note="Test note" if action == "handoff" else None)


def test_30_tickets_persist_actions_and_rerun_skips_models(tmp_path, monkeypatch):
    outcomes_path = tmp_path / "outcomes.json"
    log_path = tmp_path / "run.jsonl"
    original = (ROOT / "fixtures/tickets.json").read_bytes()
    calls = []

    def decide(state, settings):
        calls.append(state["ticket"]["id"])
        action = ("reply", "handoff", "close")[len(calls) % 3]
        return {"decision": decision(action), "model_ticket": state["ticket"]}

    monkeypatch.setattr("agent.graph.decide", decide)
    monkeypatch.setattr("agent.nodes.score.evaluate", lambda *args: {"action": 0.01})
    first = run_tickets(SETTINGS, LocalHelpdeskClient(ROOT / "fixtures", outcomes_path),
                           log_path, with_score=True)
    assert first == {"simulated": 30, "skipped": 0, "error": 0}
    saved = outcomes_path.read_bytes()
    outcomes = json.loads(saved)
    assert len(outcomes) == 30
    assert {entry["action"] for entry in outcomes.values()} == {"reply", "handoff", "close"}
    for entry in outcomes.values():
        body = entry["body"]
        assert body["confidence"] == 0.01  # low score does not override action
        assert "action" not in body
        assert ("draft_reply" in body) == (entry["action"] == "reply")
        assert ("handoff_note" in body) == (entry["action"] == "handoff")

    def unexpected(*args, **kwargs):
        raise AssertionError("Already handled tickets must not call models")

    monkeypatch.setattr("agent.graph.decide", unexpected)
    second = run_tickets(SETTINGS, LocalHelpdeskClient(ROOT / "fixtures", outcomes_path), log_path)
    assert second == {"simulated": 0, "skipped": 30, "error": 0}
    assert outcomes_path.read_bytes() == saved
    assert (ROOT / "fixtures/tickets.json").read_bytes() == original
    entries = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert len(entries) == 60
    assert all("body" not in entry and "reason" not in entry for entry in entries)


def test_failure_logs_safe_error_and_continues(tmp_path, monkeypatch):
    def decide(state, settings):
        if state["ticket"]["id"] == "T003":
            raise RuntimeError("Private provider request contents")
        return {"decision": decision("reply")}

    monkeypatch.setattr("agent.graph.decide", decide)
    client = LocalHelpdeskClient(ROOT / "fixtures", tmp_path / "outcomes.json")
    log_path = tmp_path / "run.jsonl"
    result = run_tickets(SETTINGS, client, log_path, ["T003", "T005"])
    assert result == {"simulated": 1, "skipped": 0, "error": 1}
    assert "T003" not in client.outcomes
    assert "Private" not in log_path.read_text()
    assert len(log_path.read_text().splitlines()) == 2


def test_local_helpdesk_reset(tmp_path):
    outcomes_path = tmp_path / "outcomes.json"
    client = LocalHelpdeskClient(ROOT / "fixtures", outcomes_path)
    client.record("T001", "reply", {"reason": "test"})
    assert outcomes_path.exists()
    assert "T001" in client.outcomes

    client.reset()
    assert not outcomes_path.exists()
    assert client.outcomes == {}


def test_helpdesk_client_reset(monkeypatch):
    import httpx
    from agent.clients.helpdesk import HelpdeskClient

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

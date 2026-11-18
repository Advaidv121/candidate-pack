from unittest.mock import Mock

import pytest

from agent.config import Settings
from agent.main import run_tickets
from agent.nodes.skip_done import skip_done


@pytest.mark.parametrize("handled", [True, {"action": "reply"}, False, None])
def test_skip_done_uses_current_server_status(handled):
    client = Mock()
    client.ticket.return_value = {"handled": handled}
    state = {"ticket": {"id": "T005", "handled": not bool(handled)}}

    result = skip_done(state, client)

    assert result == {"outcome": "skipped" if handled else "pending"}
    client.ticket.assert_called_once_with("T005")


@pytest.mark.parametrize("handled", [True, False])
def test_skip_done_without_client_uses_snapshot(handled):
    assert skip_done({"ticket": {"id": "T005", "handled": handled}}) == {
        "outcome": "skipped" if handled else "pending"
    }


def test_ticket_handled_after_listing_never_reaches_model(tmp_path, monkeypatch):
    client = Mock()
    client.tickets.return_value = [{
        "id": "T005", "subject": "Invite", "body": "How?", "handled": False,
    }]
    client.ticket.return_value = {"handled": {"action": "reply"}}
    decide = Mock(side_effect=AssertionError("Handled tickets must not call the model"))
    monkeypatch.setattr("agent.graph.decide", decide)
    settings = Settings("", "", "", "", "test", {})

    counts = run_tickets(settings, client, tmp_path / "run.jsonl")

    assert counts == {
        "delivered": 0, "already_handled": 0, "uncertain": 0, "skipped": 1, "error": 0,
    }
    decide.assert_not_called()
    client.post_action.assert_not_called()


def test_server_check_failure_never_reaches_model(tmp_path, monkeypatch):
    client = Mock()
    client.tickets.return_value = [{"id": "T005", "handled": False}]
    client.ticket.side_effect = RuntimeError("Server unavailable")
    decide = Mock()
    monkeypatch.setattr("agent.graph.decide", decide)
    settings = Settings("", "", "", "", "test", {})

    counts = run_tickets(settings, client, tmp_path / "run.jsonl")

    assert counts["error"] == 1
    decide.assert_not_called()
    client.post_action.assert_not_called()

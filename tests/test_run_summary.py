import json

import pytest

from agent.config import Settings
from agent.main import main, run_tickets


SETTINGS = Settings("https://helpdesk.test", "test", "test", "", "test",
                    {"helpdesk": {"timeout_s": 30}})


@pytest.mark.parametrize("reset", [False, True])
def test_cli_separates_server_totals_from_run_counts(monkeypatch, capsys, reset):
    monkeypatch.setattr("sys.argv", ["agent", "--reset"] if reset else ["agent"])
    monkeypatch.setattr("agent.main.load_settings", lambda: SETTINGS)
    monkeypatch.setattr("agent.main.HelpdeskClient.status", lambda self: {
        "open_tickets": 30 if reset else 0,
        "handled_tickets": 0 if reset else 30,
    })
    reset_calls = []
    monkeypatch.setattr("agent.main.HelpdeskClient.reset", lambda self: reset_calls.append(True))
    monkeypatch.setattr("agent.main.HelpdeskClient.tickets", lambda self, status: [])
    main()
    output = capsys.readouterr().out
    summary = json.loads(output[output.index("{"):])
    assert summary["server"] == {
        "open_tickets": 30 if reset else 0,
        "handled_tickets": 0 if reset else 30,
    }
    if reset:
        assert reset_calls == [True]
        assert "run" not in summary
    else:
        assert reset_calls == []
        assert "No open tickets to process." in output
        assert summary["run"] == {
            "processed": 0, "delivered": 0, "already_handled": 0,
            "uncertain": 0, "skipped": 0, "error": 0,
        }


def test_empty_id_selection_has_explicit_message(monkeypatch, tmp_path, capsys):
    class Client:
        def tickets(self, status):
            return [{"id": "T001"}]

    run_tickets(SETTINGS, Client(), tmp_path / "run.jsonl", ["T005"])
    assert "No open tickets matched the requested IDs." in capsys.readouterr().out

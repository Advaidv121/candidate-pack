import json

import httpx

from agent.clients.fixtures import FixtureHelpdeskClient
from agent.clients.helpdesk import HelpdeskClient


def test_fixtures_filter_handled_tickets_and_keep_labels_separate(tmp_path):
    (tmp_path / "tickets.json").write_text(json.dumps([
        {"id": "T1", "handled": False}, {"id": "T2", "handled": True}]))
    (tmp_path / "examples.json").write_text(json.dumps({
        "examples": [{"id": "E1", "label": {"action": "reply"}}]}))
    source = FixtureHelpdeskClient(tmp_path)
    assert [t["id"] for t in source.tickets()] == ["T1"]
    assert len(source.tickets(status="all")) == 2
    assert source.examples()[0]["label"]["action"] == "reply"


def test_live_reader_follows_cursor_and_preserves_filters():
    requests = []

    def respond(request):
        requests.append(request)
        assert request.url.params["status"] == "all"
        assert request.url.params["limit"] == "10"
        if "cursor" not in request.url.params:
            return httpx.Response(200, json={"tickets": [{"id": "T1"}], "next_cursor": "T1"})
        assert request.url.params["cursor"] == "T1"
        return httpx.Response(200, json={"tickets": [{"id": "T2"}], "next_cursor": None})

    with httpx.Client(base_url="https://helpdesk.test", transport=httpx.MockTransport(respond)) as transport:
        assert HelpdeskClient(transport).tickets(status="all") == [{"id": "T1"}, {"id": "T2"}]
    assert len(requests) == 2

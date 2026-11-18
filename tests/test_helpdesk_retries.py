"""Prove the helpdesk client retries the errors the API produces on purpose."""
import httpx
import pytest

from agent.clients.helpdesk import HelpdeskClient
from agent.schemas import PostBody

BODY = PostBody(language="nl", category="question", priority="P4", reason="FAQ F02")


def scripted_client(responses):
    """Feed canned HTTP responses, and record every request that was sent."""
    sent = []

    def handler(request):
        sent.append((request.method, request.url.path))
        status, payload, headers = responses.pop(0)
        return httpx.Response(status, json=payload, headers=headers)

    transport = httpx.MockTransport(handler)
    client = HelpdeskClient(httpx.Client(transport=transport, base_url="https://helpdesk.test"))
    return client, sent


def test_503_is_retried_and_posts_once(monkeypatch):
    monkeypatch.setattr("agent.clients.helpdesk.sleep", lambda seconds: None)
    client, sent = scripted_client([
        (200, {"handled": False}, {}),
        (503, {"error": "service_unavailable"}, {}),
        (200, {"ok": True}, {}),
    ])

    assert client.post_action("T005", "reply", BODY) == "delivered"
    assert sent == [
        ("GET", "/tickets/T005"),
        ("POST", "/tickets/T005/reply"),
        ("POST", "/tickets/T005/reply"),
    ]


def test_429_waits_for_retry_after(monkeypatch):
    waits = []
    monkeypatch.setattr("agent.clients.helpdesk.sleep", waits.append)
    client, sent = scripted_client([
        (200, {"handled": False}, {}),
        (429, {"error": "rate_limited"}, {"Retry-After": "2"}),
        (200, {"ok": True}, {}),
    ])

    assert client.post_action("T005", "reply", BODY) == "delivered"
    # The 0 and 0.25 entries are the fixed pacing between requests; the 2 is Retry-After.
    assert waits[2] == 2
    assert [method for method, _ in sent].count("POST") == 2


def test_409_is_not_retried(monkeypatch):
    monkeypatch.setattr("agent.clients.helpdesk.sleep", lambda seconds: None)
    client, sent = scripted_client([
        (200, {"handled": False}, {}),
        (409, {"error": "already_handled"}, {}),
    ])

    assert client.post_action("T005", "reply", BODY) == "already_handled"
    assert sent == [("GET", "/tickets/T005"), ("POST", "/tickets/T005/reply")]


def test_503_gives_up_after_three_attempts(monkeypatch):
    monkeypatch.setattr("agent.clients.helpdesk.sleep", lambda seconds: None)
    client, sent = scripted_client([
        (200, {"handled": False}, {}),
        (503, {"error": "service_unavailable"}, {}),
        (503, {"error": "service_unavailable"}, {}),
        (503, {"error": "service_unavailable"}, {}),
    ])

    with pytest.raises(httpx.HTTPStatusError):
        client.post_action("T005", "reply", BODY)
    assert [method for method, _ in sent].count("POST") == 3

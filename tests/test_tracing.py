from unittest.mock import Mock

import pytest
from langchain_core.callbacks import BaseCallbackHandler

from agent.config import Settings
from agent.graph import build_delivery_graph, build_preview_graph
from agent.tracing import with_tracing


@pytest.mark.parametrize("public_key,secret_key,enabled", [
    ("", "", "true"),
    ("pk-test", "", "true"),
    ("", "sk-test", "true"),
    ("pk-test", "sk-test", "false"),
])
def test_tracing_is_optional(monkeypatch, public_key, secret_key, enabled):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", public_key)
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", secret_key)
    monkeypatch.setenv("LANGFUSE_TRACING_ENABLED", enabled)
    handler = Mock()
    monkeypatch.setattr("agent.tracing._handler", handler)
    graph = Mock()
    assert with_tracing(graph) is graph
    handler.assert_not_called()
    graph.with_config.assert_not_called()


def test_both_graphs_attach_callback(monkeypatch, tmp_path):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    monkeypatch.setenv("LANGFUSE_TRACING_ENABLED", "true")
    handler = BaseCallbackHandler()
    monkeypatch.setattr("agent.tracing._handler", lambda: handler)
    settings = Settings("", "", "", "", "test", {})
    for graph in (build_preview_graph(settings),
                  build_delivery_graph(settings, Mock(), tmp_path / "run.jsonl")):
        assert graph.config["callbacks"] == [handler]


def test_handler_registers_flush_once(monkeypatch):
    from agent import tracing

    tracing._handler.cache_clear()
    handler = Mock()
    client = Mock()
    register = Mock()
    monkeypatch.setattr(tracing, "CallbackHandler", lambda: handler)
    monkeypatch.setattr(tracing, "get_client", lambda: client)
    monkeypatch.setattr(tracing.atexit, "register", register)
    try:
        assert tracing._handler() is handler
        assert tracing._handler() is handler
        register.assert_called_once_with(client.flush)
    finally:
        tracing._handler.cache_clear()

"""Optional Langfuse callbacks shared by preview and delivery graphs."""
import atexit
import os
from functools import lru_cache

from langfuse import get_client
from langfuse.langchain import CallbackHandler


@lru_cache(maxsize=1)
def _handler():
    langfuse_handler = CallbackHandler()
    atexit.register(get_client().flush)
    return langfuse_handler


def with_tracing(graph):
    if (not os.getenv("LANGFUSE_PUBLIC_KEY")
            or not os.getenv("LANGFUSE_SECRET_KEY")
            or os.getenv("LANGFUSE_TRACING_ENABLED", "true").lower() == "false"):
        return graph
    return graph.with_config({"callbacks": [_handler()]})

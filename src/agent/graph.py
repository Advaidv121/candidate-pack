"""Build preview and delivery workflows."""
from functools import partial
from pathlib import Path

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from agent.config import Settings
from agent.nodes.deliver import deliver
from agent.nodes.log import log
from agent.nodes.skip_done import skip_done
from agent.nodes.decide import decide
from agent.nodes.score import score
from agent.state import TicketState
from agent.tracing import with_tracing


def transient(error):
    return getattr(error, "status_code", None) in (429, 500, 502, 503, 504) or type(error).__name__ in ("Timeout", "APIConnectionError", "TimeoutError")


RETRY = RetryPolicy(max_attempts=3, retry_on=transient)


def score_with_retries(settings):
    # Keep Jev retries separate so scoring failure cannot stop delivery.
    graph = StateGraph(TicketState)
    graph.add_node("jev", partial(score, settings=settings), retry_policy=RETRY)
    graph.add_edge(START, "jev").add_edge("jev", END)
    compiled = graph.compile()

    def run(state):
        try:
            result = compiled.invoke(state)
        except Exception as error:
            return {"score_error": type(error).__name__}
        return {key: result[key] for key in ("confidence", "scores")}

    return run


def build_preview_graph(settings: Settings, with_score: bool = False):
    graph = StateGraph(TicketState)
    graph.add_node("decide", partial(decide, settings=settings), retry_policy=RETRY)
    graph.add_edge(START, "decide")
    if with_score:
        graph.add_node("score", partial(score, settings=settings))
        graph.add_edge("decide", "score")
        graph.add_edge("score", END)
    else:
        graph.add_edge("decide", END)
    return with_tracing(graph.compile())


def build_delivery_graph(settings: Settings, client,
                           log_path: Path, with_score: bool = False):
    graph = StateGraph(TicketState)
    graph.add_node("skip_done", partial(skip_done, client=client))
    graph.add_node("decide", partial(decide, settings=settings), retry_policy=RETRY)
    graph.add_node("deliver", partial(deliver, client=client))
    graph.add_node("log", partial(log, path=log_path))
    graph.add_edge(START, "skip_done")
    graph.add_conditional_edges("skip_done",
        lambda state: "log" if state["outcome"] == "skipped" else "decide")
    if with_score:
        graph.add_node("score", score_with_retries(settings))
        graph.add_edge("decide", "score")
        graph.add_edge("score", "deliver")
    else:
        graph.add_edge("decide", "deliver")
    graph.add_edge("deliver", "log")
    graph.add_edge("log", END)
    return with_tracing(graph.compile())

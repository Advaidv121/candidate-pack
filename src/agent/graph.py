from langgraph.types import RetryPolicy
"""Preview graph: prepare a ticket and draft a decision without posting."""
from functools import partial
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from agent.config import Settings
from agent.clients.fake_helpdesk import FakeHelpdeskClient
from agent.nodes.act import act
from agent.nodes.log import log
from agent.nodes.skip_done import skip_done
from agent.nodes.draft import draft
from agent.nodes.score import score
from agent.state import TicketState


def transient(error):
    return getattr(error, "status_code", None) in (429, 500, 502, 503, 504) or type(error).__name__ in ("Timeout", "APIConnectionError", "TimeoutError")


RETRY = RetryPolicy(max_attempts=3, retry_on=transient)


def optional_score(settings):
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
    graph.add_node("draft", partial(draft, settings=settings), retry_policy=RETRY)
    graph.add_edge(START, "draft")
    if with_score:
        graph.add_node("score", partial(score, settings=settings))
        graph.add_edge("draft", "score")
        graph.add_edge("score", END)
    else:
        graph.add_edge("draft", END)
    return graph.compile()


def build_simulation_graph(settings: Settings, client,
                           log_path: Path, with_score: bool = False):
    graph = StateGraph(TicketState)
    graph.add_node("skip_done", partial(skip_done, client=client))
    graph.add_node("draft", partial(draft, settings=settings), retry_policy=RETRY)
    graph.add_node("act", partial(act, client=client))
    graph.add_node("log", partial(log, path=log_path))
    graph.add_edge(START, "skip_done")
    graph.add_conditional_edges("skip_done",
        lambda state: "log" if state["outcome"] == "skipped" else "draft")
    if with_score:
        graph.add_node("score", optional_score(settings))
        graph.add_edge("draft", "score")
        graph.add_edge("score", "act")
    else:
        graph.add_edge("draft", "act")
    graph.add_edge("act", "log")
    graph.add_edge("log", END)
    return graph.compile()

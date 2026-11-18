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


def build_preview_graph(settings: Settings, with_score: bool = False):
    graph = StateGraph(TicketState)
    graph.add_node("draft", partial(draft, settings=settings))
    graph.add_edge(START, "draft")
    if with_score:
        graph.add_node("score", partial(score, settings=settings))
        graph.add_edge("draft", "score")
        graph.add_edge("score", END)
    else:
        graph.add_edge("draft", END)
    return graph.compile()


def build_simulation_graph(settings: Settings, client: FakeHelpdeskClient,
                           log_path: Path, with_score: bool = False):
    graph = StateGraph(TicketState)
    graph.add_node("skip_done", partial(skip_done, client=client))
    graph.add_node("draft", partial(draft, settings=settings))
    graph.add_node("act", partial(act, client=client))
    graph.add_node("log", partial(log, path=log_path))
    graph.add_edge(START, "skip_done")
    graph.add_conditional_edges("skip_done",
        lambda state: "log" if state["outcome"] == "skipped" else "draft")
    if with_score:
        graph.add_node("score", partial(score, settings=settings))
        graph.add_edge("draft", "score")
        graph.add_edge("score", "act")
    else:
        graph.add_edge("draft", "act")
    graph.add_edge("act", "log")
    graph.add_edge("log", END)
    return graph.compile()

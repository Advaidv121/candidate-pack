"""Preview graph: prepare a ticket and draft a decision without posting."""
from functools import partial

from langgraph.graph import END, START, StateGraph

from agent.config import Settings
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

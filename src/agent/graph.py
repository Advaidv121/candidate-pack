"""Preview graph: prepare a ticket and draft a decision without posting."""
from functools import partial

from langgraph.graph import END, START, StateGraph

from agent.config import Settings
from agent.nodes.draft import draft
from agent.state import TicketState


def build_preview_graph(settings: Settings):
    graph = StateGraph(TicketState)
    graph.add_node("draft", partial(draft, settings=settings))
    graph.add_edge(START, "draft")
    graph.add_edge("draft", END)
    return graph.compile()

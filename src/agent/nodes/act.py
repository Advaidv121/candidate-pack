"""Map the existing decision to a simulated action and API-shaped body."""
from agent.clients.fake_helpdesk import FakeHelpdeskClient
from agent.schemas import PostBody
from agent.state import TicketState


def act(state: TicketState, client: FakeHelpdeskClient) -> dict:
    fields = state["decision"].model_dump(exclude={"action"})
    fields["confidence"] = state.get("confidence")
    body = PostBody.model_validate(fields).model_dump(exclude_none=True)
    return {"outcome": client.record(state["ticket"]["id"],
                                     state["decision"].action, body)}

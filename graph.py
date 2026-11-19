from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from state import AgentState
from supervisor import supervisor_node, route
from designer import designer_node
from developer import developer_node
from review import design_review_node, code_review_node


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("supervisor", supervisor_node)
    g.add_node("designer", designer_node)
    g.add_node("developer", developer_node)
    g.add_node("design_review", design_review_node)
    g.add_node("code_review", code_review_node)

    g.add_edge(START, "supervisor")
    g.add_conditional_edges(
        "supervisor",
        route,
        {"designer": "designer", "developer": "developer", "FINISH": END},
    )

    # every agent's output goes to a human before returning to the supervisor
    g.add_edge("designer", "design_review")
    g.add_edge("design_review", "supervisor")
    g.add_edge("developer", "code_review")
    g.add_edge("code_review", "supervisor")

    # a checkpointer is REQUIRED for interrupt() - it saves the paused state
    return g.compile(checkpointer=MemorySaver())


def pending_interrupt(app, config):
    """Return the payload of the interrupt the graph is paused on, or None."""
    snapshot = app.get_state(config)
    for task in snapshot.tasks:
        if task.interrupts:
            return task.interrupts[0].value
    return None

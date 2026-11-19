from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from state import AgentState
from supervisor import supervisor_node, route
from designer import designer_node
from developer import developer_node
from review import design_review_node, merge_review_node, merge_node


def after_merge_review(state: AgentState):
    return "merge" if state.get("merge_approved") and not state.get("stopped") else "supervisor"


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("supervisor", supervisor_node)
    g.add_node("designer", designer_node)
    g.add_node("developer", developer_node)
    g.add_node("design_review", design_review_node)
    g.add_node("merge_review", merge_review_node)
    g.add_node("merge", merge_node)

    g.add_edge(START, "supervisor")
    g.add_conditional_edges(
        "supervisor",
        route,
        {"designer": "designer", "developer": "developer", "FINISH": END},
    )

    # every agent's output goes to a human before moving on
    g.add_edge("designer", "design_review")
    g.add_edge("design_review", "supervisor")
    g.add_edge("developer", "merge_review")
    # code is only written into workspace/ after the human approves the diff
    g.add_conditional_edges("merge_review", after_merge_review,
                            {"merge": "merge", "supervisor": "supervisor"})
    g.add_edge("merge", "supervisor")

    # a checkpointer is REQUIRED for interrupt() - it saves the paused state
    return g.compile(checkpointer=MemorySaver())


def pending_interrupt(app, config):
    """Return the payload of the interrupt the graph is paused on, or None."""
    snapshot = app.get_state(config)
    for task in snapshot.tasks:
        if task.interrupts:
            return task.interrupts[0].value
    return None

"""Human approval steps.

interrupt() pauses the graph and hands a payload to main.py.
main.py asks the human, then resumes the graph with their decision.
The decision becomes the return value of interrupt().

Decision format: {"action": "approve"}  or  {"action": "reject", "feedback": "..."}

On reject we clear the output and store the feedback. The supervisor then
sees the output is missing and sends the work back to the same agent,
which reads the feedback from its prompt file.
"""
from langgraph.types import interrupt
from state import AgentState


def design_review_node(state: AgentState):
    decision = interrupt({"stage": "design", "content": state.get("design")})
    if decision.get("action") == "approve":
        print("[design_review] approved")
        return {"design_feedback": None}
    print("[design_review] rejected -> back to designer")
    return {"design": None, "design_feedback": decision.get("feedback", "")}


def code_review_node(state: AgentState):
    decision = interrupt({"stage": "code", "content": state.get("code")})
    if decision.get("action") == "approve":
        print("[code_review] approved")
        return {"code_feedback": None}
    print("[code_review] rejected -> back to developer")
    return {"code": None, "code_feedback": decision.get("feedback", "")}

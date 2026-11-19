"""Human approval steps.

interrupt() pauses the graph and hands a payload to the UI (app.py or main.py).
The UI asks the human, then resumes the graph with their decision.

Decision format: {"action": "approve"}  or  {"action": "reject", "feedback": "..."}
(The UI makes the human confirm a rejection before sending it.)

On reject we clear the output and store the feedback; the supervisor sends the
work back to the same agent. After MAX_REJECTIONS rejections of the same step
the run stops and needs manual follow-up.
"""
from langgraph.types import interrupt

import workspace
from state import AgentState

MAX_REJECTIONS = 3


def _reject(state, kind: str, label: str, decision: dict, cleared: dict):
    """kind = state-field prefix ("design" / "code"); label = what the human reviewed."""
    count = (state.get(f"{kind}_rejections") or 0) + 1
    if count >= MAX_REJECTIONS:
        print(f"[{label} review] rejected {count} times -> stopped")
        return {f"{kind}_rejections": count,
                "stopped": f"{label.capitalize()} rejected {count} times. Needs manual follow-up."}
    print(f"[{label} review] rejected -> back with feedback")
    return {**cleared, f"{kind}_rejections": count, f"{kind}_feedback": decision.get("feedback", "")}


def design_review_node(state: AgentState):
    decision = interrupt({
        "stage": "design",
        "content": state.get("design"),
        "rejections_left": MAX_REJECTIONS - (state.get("design_rejections") or 0),
    })
    if decision.get("action") == "approve":
        print("[design_review] approved")
        return {"design_feedback": None}
    return _reject(state, "design", "design", decision, {"design": None})


def merge_review_node(state: AgentState):
    changes = state.get("changes") or []
    decision = interrupt({
        "stage": "merge",
        "content": state.get("code"),
        "diff": state.get("diff"),
        "files": [{"path": c["path"], "status": "added" if c["old"] is None else "modified"}
                  for c in changes],
        "rejections_left": MAX_REJECTIONS - (state.get("code_rejections") or 0),
    })
    if decision.get("action") == "approve":
        print("[merge_review] approved")
        return {"code_feedback": None, "merge_approved": True}
    return _reject(state, "code", "code changes", decision, {"code": None, "changes": None, "diff": None})


def merge_node(state: AgentState):
    try:
        files = workspace.apply(state.get("changes") or [])
    except RuntimeError as e:
        print(f"[merge] conflict: {e}")
        return {"stopped": f"Merge conflict: {e}"}
    print(f"[merge] wrote {files} to workspace/")
    return {"merged_files": files}

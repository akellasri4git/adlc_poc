from llm import llm
from state import AgentState
from prompt_loader import load_prompt


def developer_node(state: AgentState):
    prompt = load_prompt(
        "developer",
        requirement=state["requirement"],
        design=state.get("design") or "No design provided.",
        feedback=state.get("code_feedback") or "",
    )
    msg = llm.invoke(prompt)
    print("[developer] done")
    return {"code": msg.content}

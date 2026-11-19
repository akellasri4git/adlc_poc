from llm import llm
from state import AgentState
from prompt_loader import load_prompt


def designer_node(state: AgentState):
    prompt = load_prompt(
        "designer",
        requirement=state["requirement"],
        feedback=state.get("design_feedback") or "",
    )
    msg = llm.invoke(prompt)
    print("[designer] done")
    return {"design": msg.content}

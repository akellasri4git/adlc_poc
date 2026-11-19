from typing import Literal
from pydantic import BaseModel
from llm import llm
from state import AgentState
from prompt_loader import load_prompt


class Intent(BaseModel):
    intent: Literal["design_only", "code_only", "full_cycle"]


classifier = llm.with_structured_output(Intent)


def supervisor_node(state: AgentState):
    # 1. Classify intent only once, on the first visit
    intent = state.get("intent")
    if not intent:
        prompt = load_prompt("supervisor", requirement=state["requirement"])
        intent = classifier.invoke(prompt).intent

    # 2. Route based on intent + what is already done (and approved)
    needs_design = intent in ("design_only", "full_cycle")
    needs_code = intent in ("code_only", "full_cycle")

    if state.get("stopped"):
        nxt = "FINISH"
    elif needs_design and not state.get("design"):
        nxt = "designer"
    elif needs_code and not state.get("merged_files") and not state.get("code"):
        nxt = "developer"
    else:
        nxt = "FINISH"

    print(f"[supervisor] intent={intent} -> {nxt}")
    return {"intent": intent, "next": nxt}


def route(state: AgentState):
    return state["next"]

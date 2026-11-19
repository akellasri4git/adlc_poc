"""Runs every user story in stories/*.md through the graph, in the terminal.

Normal run (asks you to approve each design / code):
    python3 main.py

Fully automatic run (approves everything, no questions):
    macOS / Linux:  AUTO_APPROVE=true python3 main.py
    PowerShell:     $env:AUTO_APPROVE="true"; python main.py

For the browser version, see app.py.
"""
import os
from langgraph.types import Command
from graph import build_graph, pending_interrupt
from story_loader import load_stories, story_to_requirement

AUTO_APPROVE = os.getenv("AUTO_APPROVE", "false").lower() == "true"


def ask_human(payload: dict) -> dict:
    print("\n" + "=" * 60)
    print(f"APPROVAL NEEDED: {payload['stage'].upper()}")
    print("-" * 60)
    print(payload["content"])
    print("=" * 60)

    if AUTO_APPROVE:
        print("(AUTO_APPROVE on -> approved)")
        return {"action": "approve"}

    answer = input("Approve? [y = yes / n = reject]: ").strip().lower()
    if answer == "y":
        return {"action": "approve"}
    feedback = input("What should be changed? ")
    return {"action": "reject", "feedback": feedback}


def run_requirement(app, name: str, requirement: str):
    print(f"\n\n######## {requirement}")
    config = {"configurable": {"thread_id": name}}  # one thread per requirement

    app.invoke({"requirement": requirement}, config)

    # keep resuming until the graph stops asking for approval
    while (payload := pending_interrupt(app, config)) is not None:
        decision = ask_human(payload)
        app.invoke(Command(resume=decision), config)

    result = app.get_state(config).values
    print("\nINTENT:", result.get("intent"))
    print("\nDESIGN:\n", result.get("design"))
    print("\nCODE:\n", result.get("code"))
    return result


if __name__ == "__main__":
    print("main.py started")
    app = build_graph()
    for story in load_stories():
        run_requirement(app, story["id"], story_to_requirement(story))

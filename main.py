"""Runs every requirement in requirements/*.txt through the graph.

Normal run (asks you to approve each design / code):
    python main.py

Fully automatic run (approves everything, no questions):
    PowerShell:  $env:AUTO_APPROVE="true"; python main.py
"""
import os
from pathlib import Path
from langgraph.types import Command
from graph import build_graph

AUTO_APPROVE = os.getenv("AUTO_APPROVE", "false").lower() == "true"
REQUIREMENTS_DIR = Path(__file__).parent / "requirements"


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


def pending_interrupt(app, config):
    """Return the payload of the interrupt the graph is paused on, or None."""
    snapshot = app.get_state(config)
    for task in snapshot.tasks:
        if task.interrupts:
            return task.interrupts[0].value
    return None


def run_requirement(app, name: str, requirement: str):
    print(f"\n\n######## {name}: {requirement}")
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
    for file in sorted(REQUIREMENTS_DIR.glob("*.txt")):
        run_requirement(app, file.stem, file.read_text(encoding="utf-8").strip())

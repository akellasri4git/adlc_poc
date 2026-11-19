"""Runs every user story in stories/*.md through the graph, in the terminal.

Normal run (asks you to approve each design / merge):
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
    stage = "MERGE CODE CHANGES" if payload["stage"] == "merge" else payload["stage"].upper()
    print("\n" + "=" * 60)
    print(f"APPROVAL NEEDED: {stage}   (rejections left: {payload['rejections_left']})")
    print("-" * 60)
    print(payload["content"])
    if payload.get("diff"):
        print("-" * 60)
        print(payload["diff"])
    print("=" * 60)

    if AUTO_APPROVE:
        print("(AUTO_APPROVE on -> approved)")
        return {"action": "approve"}

    while True:
        answer = input("Approve? [y = approve / n = reject]: ").strip().lower()
        if answer == "y":
            return {"action": "approve"}
        if answer != "n":
            continue
        feedback = ""
        while not feedback:
            feedback = input("What should be changed? ").strip()
        confirm = input(f'Reject with feedback "{feedback}"? [y = confirm / n = cancel]: ').strip().lower()
        if confirm == "y":
            return {"action": "reject", "feedback": feedback}
        print("Rejection cancelled.")


def run_story(app, story: dict):
    requirement = story_to_requirement(story)
    print(f"\n\n######## {requirement.splitlines()[0]}")
    config = {"configurable": {"thread_id": story["id"]}}

    app.invoke({"requirement": requirement}, config)

    # keep resuming until the graph stops asking for approval
    while (payload := pending_interrupt(app, config)) is not None:
        app.invoke(Command(resume=ask_human(payload)), config)

    result = app.get_state(config).values
    print("\nINTENT:", result.get("intent"))
    if result.get("stopped"):
        print("STOPPED:", result["stopped"])
    if result.get("design"):
        print("\nDESIGN:\n", result["design"])
    if result.get("merged_files") is not None:
        print("\nMERGED into workspace/:", ", ".join(result["merged_files"]) or "(no changes)")
    return result


if __name__ == "__main__":
    print("main.py started")
    app = build_graph()
    for story in load_stories():
        run_story(app, story)

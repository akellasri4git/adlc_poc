"""Browser version of the ADLC demo.

Start it:
    uvicorn app:app --reload
Then open http://localhost:8000

Pick a user story, run it, and approve or reject the design and the code merge in the page.
The same graph, agents and MOCK setting (.env) as main.py are used.
"""
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from langgraph.types import Command
from pydantic import BaseModel

import workspace
from graph import build_graph, pending_interrupt
from llm import MOCK
from story_loader import get_story, load_stories, story_to_requirement

app = FastAPI(title="ADLC demo")
graph = build_graph()
runs: dict[str, dict] = {}  # run_id -> {"story_id", "steps"}; graph state lives in the checkpointer

INDEX_HTML = Path(__file__).parent / "static" / "index.html"


class RunRequest(BaseModel):
    story_id: str


class Decision(BaseModel):
    action: str  # "approve" or "reject"
    feedback: str = ""


def _advance(run_id: str, graph_input) -> dict:
    """Run the graph until it pauses for approval or finishes, recording each step."""
    config = {"configurable": {"thread_id": run_id}}
    for update in graph.stream(graph_input, config, stream_mode="updates"):
        for node, values in update.items():
            if node == "__interrupt__":
                continue
            values = values or {}
            runs[run_id]["steps"].append({"node": node, "detail": _describe(node, values)})
    return _status(run_id)


def _describe(node: str, values: dict) -> str:
    if node == "supervisor":
        return f"intent = {values.get('intent')} → next: {values.get('next')}"
    if node.endswith("_review"):
        if values.get("stopped"):
            return "rejected → limit reached, run stopped"
        if any(k.endswith("_feedback") and v for k, v in values.items()):
            return "rejected → sent back with feedback"
        return "approved"
    if node == "developer":
        return f"proposed changes to {len(values.get('changes') or [])} file(s)"
    if node == "merge":
        if values.get("stopped"):
            return "merge failed: " + values["stopped"]
        return "merged into workspace/: " + (", ".join(values.get("merged_files") or []) or "no changes")
    return "output ready for review"


def _status(run_id: str) -> dict:
    config = {"configurable": {"thread_id": run_id}}
    payload = pending_interrupt(graph, config)
    values = graph.get_state(config).values
    return {
        "run_id": run_id,
        "story_id": runs[run_id]["story_id"],
        "status": "awaiting_approval" if payload else ("stopped" if values.get("stopped") else "done"),
        "pending": payload,
        "steps": runs[run_id]["steps"],
        "result": {
            "intent": values.get("intent"),
            "design": values.get("design"),
            "summary": values.get("code"),
            "diff": values.get("diff"),
            "merged_files": values.get("merged_files"),
            "stopped": values.get("stopped"),
        },
    }


@app.get("/", response_class=HTMLResponse)
def index():
    return INDEX_HTML.read_text(encoding="utf-8")


@app.get("/api/config")
def config():
    return {"mock": MOCK}


@app.post("/api/workspace/reset")
def reset_workspace():
    workspace.reset_workspace()
    return {"ok": True, "files": list(workspace.read_files())}


@app.get("/api/stories")
def stories():
    return load_stories()


@app.post("/api/runs")
def start_run(req: RunRequest):
    story = get_story(req.story_id)
    if not story:
        raise HTTPException(404, f"Story {req.story_id} not found")
    run_id = uuid.uuid4().hex[:8]  # a fresh thread each time, so a story can be re-run
    runs[run_id] = {"story_id": story["id"], "steps": []}
    return _advance(run_id, {"requirement": story_to_requirement(story)})


@app.post("/api/runs/{run_id}/decision")
def decide(run_id: str, decision: Decision):
    if run_id not in runs:
        raise HTTPException(404, "Run not found")
    if _status(run_id)["status"] != "awaiting_approval":
        raise HTTPException(409, "This run is not waiting for approval")
    if decision.action not in ("approve", "reject"):
        raise HTTPException(400, "action must be 'approve' or 'reject'")
    return _advance(run_id, Command(resume=decision.model_dump()))


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    if run_id not in runs:
        raise HTTPException(404, "Run not found")
    return _status(run_id)

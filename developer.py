from pydantic import BaseModel

import workspace
from llm import llm
from prompt_loader import load_prompt
from state import AgentState


class FileChange(BaseModel):
    path: str
    content: str


class CodeChanges(BaseModel):
    summary: str
    files: list[FileChange]


coder = llm.with_structured_output(CodeChanges)


def developer_node(state: AgentState):
    existing = workspace.read_files()
    prompt = load_prompt(
        "developer",
        requirement=state["requirement"],
        design=state.get("design") or "No design provided.",
        files=workspace.as_prompt(existing),
        feedback=state.get("code_feedback") or "",
    )
    result = coder.invoke(prompt)

    changes = []
    for f in result.files:
        if workspace.safe_path(f.path) is None:
            print(f"[developer] skipped unsafe path {f.path!r}")
            continue
        old = existing.get(f.path)
        if old != f.content:
            changes.append({"path": f.path, "old": old, "new": f.content})

    print(f"[developer] proposed changes to {len(changes)} file(s)")
    return {
        "code": result.summary or "(no summary)",
        "changes": changes,
        "diff": workspace.diff(changes) or "(no changes proposed)",
        "merge_approved": False,
    }

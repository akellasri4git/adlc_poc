from typing import TypedDict, Optional


class AgentState(TypedDict, total=False):
    requirement: str
    intent: Optional[str]
    design: Optional[str]
    next: str
    # developer output: proposed changes to the existing code in workspace/
    code: Optional[str]            # one-line summary of the change
    changes: Optional[list]        # [{"path", "old", "new"}]
    diff: Optional[str]            # unified diff shown at merge review
    merge_approved: bool
    merged_files: Optional[list]
    # human-in-the-loop fields
    design_feedback: Optional[str]
    code_feedback: Optional[str]
    design_rejections: int
    code_rejections: int
    stopped: Optional[str]         # reason the run ended early

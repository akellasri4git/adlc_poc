from typing import TypedDict, Optional


class AgentState(TypedDict, total=False):
    requirement: str
    intent: Optional[str]
    design: Optional[str]
    code: Optional[str]
    next: str
    # human-in-the-loop fields
    design_feedback: Optional[str]
    code_feedback: Optional[str]

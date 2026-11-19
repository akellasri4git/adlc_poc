"""Reads Jira-style user stories from stories/*.md.

Expected format of each file:

    # ADLC-101: Story title

    ## Description
    As a ..., I want ..., so that ...

    ## Acceptance Criteria
    - first criterion
    - second criterion
"""
import re
from pathlib import Path

STORIES_DIR = Path(__file__).parent / "stories"


def parse_story(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")

    header = re.search(r"^#\s+([A-Z][A-Z0-9]*-\d+)\s*:\s*(.+)$", text, re.MULTILINE)
    if not header:
        raise ValueError(f"{path.name}: first heading must look like '# ADLC-101: Title'")

    sections = {}
    for match in re.finditer(r"^##\s+(.+?)\s*$\n(.*?)(?=^##\s|\Z)", text, re.MULTILINE | re.DOTALL):
        sections[match.group(1).strip().lower()] = match.group(2).strip()

    criteria = [
        line.lstrip("-* ").strip()
        for line in sections.get("acceptance criteria", "").splitlines()
        if line.strip().startswith(("-", "*"))
    ]

    return {
        "id": header.group(1),
        "title": header.group(2).strip(),
        "description": sections.get("description", ""),
        "acceptance_criteria": criteria,
        "file": path.name,
    }


def load_stories() -> list[dict]:
    return [parse_story(p) for p in sorted(STORIES_DIR.glob("*.md"))]


def get_story(story_id: str) -> dict | None:
    return next((s for s in load_stories() if s["id"] == story_id), None)


def story_to_requirement(story: dict) -> str:
    """The text the agents receive. The first line is always 'ID: Title'."""
    criteria = "\n".join(f"- {c}" for c in story["acceptance_criteria"])
    return (
        f"{story['id']}: {story['title']}\n\n"
        f"Description:\n{story['description']}\n\n"
        f"Acceptance Criteria:\n{criteria}"
    )

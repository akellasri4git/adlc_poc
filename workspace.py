"""The 'existing codebase' the Developer changes.

sample_project/  = the original code, kept in git (never modified)
workspace/       = the working copy that approved merges are written into
                   (git-ignored; created from sample_project/ on first use,
                    and restored by reset_workspace())
"""
import difflib
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
SAMPLE_DIR = ROOT / "sample_project"
WORKSPACE_DIR = ROOT / "workspace"


def ensure_workspace():
    if not WORKSPACE_DIR.exists():
        shutil.copytree(SAMPLE_DIR, WORKSPACE_DIR)


def reset_workspace():
    if WORKSPACE_DIR.exists():
        shutil.rmtree(WORKSPACE_DIR)
    shutil.copytree(SAMPLE_DIR, WORKSPACE_DIR)


def read_files() -> dict[str, str]:
    ensure_workspace()
    return {
        str(p.relative_to(WORKSPACE_DIR)): p.read_text(encoding="utf-8")
        for p in sorted(WORKSPACE_DIR.rglob("*.py"))
        if "__pycache__" not in p.parts
    }


def as_prompt(files: dict[str, str]) -> str:
    return "\n".join(f"### FILE: {path}\n{text}\n### END FILE" for path, text in files.items())


def safe_path(rel: str) -> Path | None:
    """Resolve a path inside workspace/, or None if it tries to escape it."""
    target = (WORKSPACE_DIR / rel).resolve()
    return target if target.is_relative_to(WORKSPACE_DIR.resolve()) else None


def diff(changes: list[dict]) -> str:
    out = []
    for c in changes:
        out.extend(difflib.unified_diff(
            (c["old"] or "").splitlines(keepends=True),
            c["new"].splitlines(keepends=True),
            fromfile="/dev/null" if c["old"] is None else f"a/{c['path']}",
            tofile=f"b/{c['path']}",
        ))
    return "".join(out)


def apply(changes: list[dict]) -> list[str]:
    """Write approved changes. Refuses if a file changed since the proposal."""
    current = read_files()
    for c in changes:
        if current.get(c["path"]) != c["old"]:
            raise RuntimeError(
                f"{c['path']} changed after the code was proposed "
                "(another merge or a reset). Run the story again."
            )
    for c in changes:
        path = safe_path(c["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(c["new"], encoding="utf-8")
    return [c["path"] for c in changes]

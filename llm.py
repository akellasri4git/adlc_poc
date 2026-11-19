"""Provides the `llm` object every agent imports.

Set MOCK in .env (or the environment):
    MOCK=true   -> fake LLM, no API key or internet needed (default)
    MOCK=false  -> real Claude model via langchain-anthropic; needs ANTHROPIC_API_KEY

The fake LLM supports the same two calls the agents make:
    llm.invoke(prompt).content
    llm.with_structured_output(Schema).invoke(prompt)
"""
import os
import re
from pathlib import Path

from langchain_core.messages import AIMessage

ENV_FILE = Path(__file__).parent / ".env"


def _load_env_file():
    """Read KEY=VALUE lines from .env. Real environment variables win."""
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file()
MOCK = os.getenv("MOCK", "true").lower() == "true"


def _field(prompt: str, label: str) -> str:
    """Pull the text after 'Label:' (or the line after 'for:') out of a prompt."""
    match = re.search(rf"{label}:\s*(.*)", prompt)
    return match.group(1).strip() if match else ""


class _FakeStructured:
    def __init__(self, schema):
        self.schema = schema

    def invoke(self, prompt: str):
        if self.schema.__name__ == "CodeChanges":
            return self.schema.model_validate(_mock_code_changes(prompt))

        # Supervisor: guess the intent from keywords.
        req = prompt.split("Requirement:", 1)[-1].lower()
        if re.search(r"only (the )?design", req):
            intent = "design_only"
        elif re.search(r"only (the )?code", req):
            intent = "code_only"
        else:
            intent = "full_cycle"
        return self.schema(intent=intent)


def _criteria(prompt: str) -> list[str]:
    """Acceptance criteria bullets from the story text inside a prompt."""
    if "Acceptance Criteria:" not in prompt:
        return []
    block = prompt.split("Acceptance Criteria:", 1)[1]
    items = []
    for line in block.splitlines()[1:]:
        if not line.startswith("- "):
            break
        items.append(line[2:].strip())
    return items


_STOPWORDS = {"a", "an", "the", "user", "users", "can", "with", "and", "to", "of", "is",
              "are", "be", "by", "for", "in", "on", "their", "they", "every", "all", "when"}


def _func_name(criterion: str) -> str:
    plain = re.sub(r"'s\b", "", criterion.lower())
    words = [w for w in re.findall(r"[a-z0-9]+", plain) if w not in _STOPWORDS]
    name = "_".join(words[:4]) or "criterion"
    return name if name[0].isalpha() else f"ac_{name}"


def _mock_code_changes(prompt: str) -> dict:
    """Fake developer: bump VERSION and add one stub function per acceptance criterion
    to the existing file that matches the story (or a new file if none matches)."""
    first_line = _field(prompt, "Requirement")            # "ADLC-101: Title"
    story_id, _, title = first_line.partition(":")
    story_id, title = story_id.strip(), title.strip()
    feedback = _field(prompt, r"\(empty if first attempt\)")
    files = dict(re.findall(r"### FILE: (.+?)\n(.*?)\n### END FILE", prompt, re.DOTALL))

    key = re.sub(r"[^a-z0-9]", "", title.lower())
    target = next((p for p in files if Path(p).stem.split("_")[0] in key), None)
    if target:
        text = files[target]
    else:
        target = story_id.lower().replace("-", "_") + ".py"
        text = f'"""{title} (new module)."""\n\nVERSION = "1.0.0"\n'

    # remove this story's block from an earlier merge, so re-runs replace it
    text = re.sub(rf"\n*# --- {re.escape(story_id)}: .*?# --- end {re.escape(story_id)} ---\n?",
                  "\n", text, flags=re.DOTALL).rstrip("\n") + "\n"
    text = re.sub(r'VERSION = "(\d+)\.(\d+)\.\d+"',
                  lambda m: f'VERSION = "{m[1]}.{int(m[2]) + 1}.0"', text, count=1)

    block = [f"\n\n# --- {story_id}: {title} ---"]
    if feedback:
        block.append(f"# Reviewer feedback addressed: {feedback}")
    for i, c in enumerate(_criteria(prompt), 1):
        block.append(f'\n\ndef {_func_name(c)}():\n    """AC{i}: {c}"""\n'
                     f'    raise NotImplementedError("TODO: implement")')
    block.append(f"\n\n# --- end {story_id} ---\n")

    action = "updated" if target in files else "created"
    return {
        "summary": f"[MOCK] {story_id}: {action} {target} for {len(_criteria(prompt))} acceptance criteria",
        "files": [{"path": target, "content": text + "\n".join(block)}],
    }


class FakeLLM:
    """Returns canned answers built from the prompt, so the whole graph can run offline."""

    def invoke(self, prompt: str) -> AIMessage:
        feedback = _field(prompt, r"\(empty if first attempt\)")
        note = f"\n(revised after feedback: {feedback})" if feedback else ""

        criteria = _criteria(prompt)

        if prompt.startswith("You are a software designer"):
            req = prompt.split("for:", 1)[1].split("\n")[1].strip()
            covered = "\n".join(f"  [x] {c}" for c in criteria)
            text = (
                f"[MOCK DESIGN] {req}\n"
                "- Client sends HTTP requests\n"
                "- API layer validates input\n"
                "- Service layer holds business logic\n"
                "- Repository layer stores data\n"
                "- Responses returned as JSON"
                + (f"\nAcceptance criteria covered:\n{covered}" if covered else "")
            )
        elif prompt.startswith("You are a python developer"):
            req = _field(prompt, "Requirement")
            handlers = "\n\n".join(
                f"def criterion_{i}():\n    \"\"\"{c}\"\"\"\n    raise NotImplementedError"
                for i, c in enumerate(criteria, 1)
            )
            text = (
                f"# [MOCK CODE] {req}\n\n"
                + (handlers + "\n\n" if handlers else "")
                + "def main():\n"
                f"    print({req!r})\n\n"
                "if __name__ == '__main__':\n"
                "    main()"
            )
        else:
            text = "[MOCK] response"
        return AIMessage(content=text + note)

    def with_structured_output(self, schema):
        return _FakeStructured(schema)


def _real_llm():
    from langchain_anthropic import ChatAnthropic  # only needed when MOCK=false

    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("MOCK=false but ANTHROPIC_API_KEY is not set (add it to .env).")
    return ChatAnthropic(model=os.getenv("LLM_MODEL", "claude-sonnet-5-5"), temperature=0)


llm = FakeLLM() if MOCK else _real_llm()
print(f"[llm] {'MOCK (fake LLM)' if MOCK else 'REAL (' + os.getenv('LLM_MODEL', 'claude-sonnet-5-5') + ')'}")

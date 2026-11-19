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
        # Only the supervisor uses structured output: guess the intent from keywords.
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

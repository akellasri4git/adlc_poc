from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(name: str, **values) -> str:
    """Read prompts/<name>.txt and fill in {placeholders}.

    Example: load_prompt("designer", requirement="...", feedback="")
    Note: if you need a literal { or } in a prompt file, write {{ or }}.
    """
    template = (PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8")
    return template.format(**values)

"""
ai.py - AI project planner. Turns a plain-language project idea into a
structured set of Kanban tasks using Claude (Anthropic).

The API key never leaves the server. Returns [] gracefully if unconfigured.
"""
import json
import os

from .config import settings

try:
    import anthropic
    _HAS_ANTHROPIC = True
except ImportError:  # pragma: no cover
    _HAS_ANTHROPIC = False

_SYSTEM = (
    "You are an expert agile project manager. Given a project idea, break it down "
    "into a clear, well-ordered set of Kanban tasks following best practices:\n"
    "- 6 to 14 concrete, actionable tasks (verb-first titles).\n"
    "- Sequence them logically and set realistic priorities (High/Medium/Low).\n"
    "- Most tasks start in the 'ToDo' column; only put a task in 'Doing'/'Done' if the "
    "idea clearly implies it is already underway or finished.\n"
    "- Add 1-3 short tags per task to group related work.\n"
    "- Give each task a one-sentence description with the concrete outcome.\n"
    "- Avoid vague tasks ('work on X'); make each independently checkable.\n"
    "Write every task in the SAME LANGUAGE as the project idea."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "description": {"type": "string"},
                    "priority": {"type": "string", "enum": ["High", "Medium", "Low"]},
                    "column_name": {"type": "string", "enum": ["ToDo", "Doing", "Done"]},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["text", "description", "priority", "column_name", "tags"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["tasks"],
    "additionalProperties": False,
}


def configured() -> bool:
    return bool(_HAS_ANTHROPIC and (settings.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")))


def _client():
    if settings.anthropic_api_key:
        return anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return anthropic.Anthropic()  # resolves ANTHROPIC_API_KEY / profile from env


def generate_plan(idea: str) -> list[dict]:
    """Return a list of task dicts for the given project idea."""
    if not configured():
        raise RuntimeError("AI planner not configured")
    response = _client().messages.create(
        model=settings.anthropic_model,
        max_tokens=4096,
        system=_SYSTEM,
        messages=[{"role": "user", "content": f"Project idea:\n{idea.strip()}"}],
        output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
    )
    text = next((b.text for b in response.content if b.type == "text"), "{}")
    data = json.loads(text)
    return data.get("tasks", [])

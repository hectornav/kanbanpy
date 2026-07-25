"""
ai.py - AI project planner. Turns a plain-language project idea into a
structured set of Kanban tasks.

Two providers, chosen via KANBAN_AI_PROVIDER:
  * "anthropic" — Claude (cloud). API key stays server-side.
  * "ollama"    — a local model on your NAS/host (no API key, fully private).

Returns [] / raises gracefully if unconfigured.
"""
import json
import os
import urllib.error
import urllib.request

from . import db
from .config import settings

try:
    import anthropic
    _HAS_ANTHROPIC = True
except ImportError:  # pragma: no cover
    _HAS_ANTHROPIC = False


def config() -> dict:
    """Resolve AI config: DB settings (editable in-app) override env defaults."""
    return {
        "provider": db.get_setting("ai_provider", settings.ai_provider) or settings.ai_provider,
        "anthropic_api_key": db.get_setting("anthropic_api_key", settings.anthropic_api_key),
        "anthropic_model": db.get_setting("anthropic_model", settings.anthropic_model) or settings.anthropic_model,
        "openai_base_url": db.get_setting("openai_base_url", settings.openai_base_url) or settings.openai_base_url,
        "openai_api_key": db.get_setting("openai_api_key", settings.openai_api_key),
        "openai_model": db.get_setting("openai_model", settings.openai_model) or settings.openai_model,
        "ollama_url": db.get_setting("ollama_url", settings.ollama_url) or settings.ollama_url,
        "ollama_model": db.get_setting("ollama_model", settings.ollama_model) or settings.ollama_model,
    }

_SYSTEM = (
    "You are an expert agile project manager. Given a project idea, break it down "
    "into a clear, well-ordered set of Kanban tasks following best practices:\n"
    "- 6 to 14 concrete, actionable tasks (verb-first titles).\n"
    "- Sequence them logically and set realistic priorities (High/Medium/Low).\n"
    "- Most tasks start in the 'ToDo' column; only put a task in 'Doing'/'Done' if the "
    "idea clearly implies it is already underway or finished. Use 'Backlog' only for "
    "tasks that are clearly lower-priority, speculative, or not part of the immediate "
    "next steps.\n"
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
                    "column_name": {"type": "string", "enum": ["Backlog", "ToDo", "Doing", "Done"]},
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

# JSON shape hint for providers that don't enforce a schema natively (OpenAI-compatible).
_SYSTEM_JSON = _SYSTEM + (
    "\n\nReturn ONLY a JSON object (no prose, no markdown) of the form:\n"
    '{"tasks": [{"text": string, "description": string, '
    '"priority": "High|Medium|Low", "column_name": "Backlog|ToDo|Doing|Done", "tags": [string]}]}'
)


def anthropic_key_set() -> bool:
    return bool(config()["anthropic_api_key"] or os.getenv("ANTHROPIC_API_KEY"))


def openai_key_set() -> bool:
    return bool(config()["openai_api_key"])


def configured() -> bool:
    c = config()
    if c["provider"] == "ollama":
        return True  # reachability is checked when a plan is generated
    if c["provider"] == "openai":
        return bool(c["openai_api_key"] and c["openai_base_url"])
    return bool(_HAS_ANTHROPIC and (c["anthropic_api_key"] or os.getenv("ANTHROPIC_API_KEY")))


def generate_plan(idea: str) -> list[dict]:
    """Return a list of task dicts for the given project idea."""
    c = config()
    if not configured():
        raise RuntimeError("AI planner not configured")
    if c["provider"] == "ollama":
        return _generate_ollama(idea, c)
    if c["provider"] == "openai":
        return _generate_openai(idea, c)
    return _generate_anthropic(idea, c)


# ── Anthropic (Claude) ──────────────────────────────────────────────────────

def _anthropic_client(c: dict):
    if c["anthropic_api_key"]:
        return anthropic.Anthropic(api_key=c["anthropic_api_key"])
    return anthropic.Anthropic()  # resolves ANTHROPIC_API_KEY / profile from env


def _generate_anthropic(idea: str, c: dict) -> list[dict]:
    response = _anthropic_client(c).messages.create(
        model=c["anthropic_model"],
        max_tokens=4096,
        system=_SYSTEM,
        messages=[{"role": "user", "content": f"Project idea:\n{idea.strip()}"}],
        output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
    )
    text = next((b.text for b in response.content if b.type == "text"), "{}")
    return json.loads(text).get("tasks", [])


# ── Ollama (local) ──────────────────────────────────────────────────────────

def _generate_ollama(idea: str, c: dict) -> list[dict]:
    payload = {
        "model": c["ollama_model"],
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": f"Project idea:\n{idea.strip()}"},
        ],
        "stream": False,
        "format": _SCHEMA,  # Ollama constrains output to this JSON schema
        "options": {"temperature": 0.4},
    }
    req = urllib.request.Request(
        c["ollama_url"].rstrip("/") + "/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = json.loads(resp.read())
    content = body.get("message", {}).get("content", "{}")
    return json.loads(content).get("tasks", [])


# ── OpenAI-compatible (OpenAI, Groq, OpenRouter, Together, LM Studio, …) ─────

def _generate_openai(idea: str, c: dict) -> list[dict]:
    payload = {
        "model": c["openai_model"],
        "messages": [
            {"role": "system", "content": _SYSTEM_JSON},
            {"role": "user", "content": f"Project idea:\n{idea.strip()}"},
        ],
        "temperature": 0.4,
        "response_format": {"type": "json_object"},  # widely supported; forces valid JSON
    }
    req = urllib.request.Request(
        c["openai_base_url"].rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {c['openai_api_key']}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = json.loads(resp.read())
    content = body["choices"][0]["message"]["content"]
    return json.loads(content).get("tasks", [])

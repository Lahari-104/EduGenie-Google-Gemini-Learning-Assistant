"""
learning_path.py — Personalized Learning Recommendations.

Exposes generate_learning_path(topic) -> dict

Returns a roadmap shaped for the frontend:
    {
        "beginner":     [str, ...],
        "intermediate": [str, ...],
        "advanced":     [str, ...]
    }

Each item combines a skill/topic with a recommended resource.
"""

from __future__ import annotations

from typing import Any

from utils import GeminiError, extract_json, generate_text

_SYSTEM = (
    "You are EduGenie, a learning-path designer. "
    "You build practical, well-sequenced roadmaps and recommend concrete, well-known "
    "learning resources. You always respond with valid JSON and nothing else."
)

_PROMPT_TEMPLATE = (
    'Create a learning roadmap for someone who wants to learn: "{topic}".\n\n'
    "Respond with ONLY a JSON object with exactly these three keys:\n"
    '  "beginner", "intermediate", "advanced"\n'
    "Each key maps to an array of 3 to 5 strings. Each string should name a specific "
    "skill or subtopic followed by a recommended resource, using this style:\n"
    '  "Variables and data types — freeCodeCamp Python course"\n\n'
    "Order items from foundational to advanced within each level. "
    "Do not include markdown or any text outside the JSON object."
)


def generate_learning_path(topic: str) -> dict[str, list[str]]:
    """Generate a beginner/intermediate/advanced roadmap for a topic."""
    prompt = _PROMPT_TEMPLATE.format(topic=topic)
    raw = generate_text(prompt, system_instruction=_SYSTEM, temperature=0.5, as_json=True)
    data = extract_json(raw)
    return _normalize_path(data)


def _normalize_path(data: Any) -> dict[str, list[str]]:
    """Coerce the model output into the three-level dict the frontend expects."""
    if not isinstance(data, dict):
        raise GeminiError("Couldn't build a learning path. Please try again.")

    result: dict[str, list[str]] = {}
    for level in ("beginner", "intermediate", "advanced"):
        value = data.get(level, [])
        items: list[str] = []

        if isinstance(value, list):
            for entry in value:
                text = _stringify_entry(entry)
                if text:
                    items.append(text)
        elif isinstance(value, str) and value.strip():
            items.append(value.strip())

        result[level] = items

    if not any(result.values()):
        raise GeminiError("Couldn't build a learning path. Please try again.")

    return result


def _stringify_entry(entry: Any) -> str:
    """Turn a roadmap entry (string or object) into a single display string."""
    if entry is None:
        return ""
    if isinstance(entry, str):
        return entry.strip()
    if isinstance(entry, dict):
        parts = [str(v).strip() for v in entry.values() if str(v).strip()]
        return " — ".join(parts)
    return str(entry).strip()

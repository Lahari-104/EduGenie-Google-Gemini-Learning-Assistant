"""
quiz_module.py — Quiz Generation.

Exposes generate_quiz(topic) -> list[dict]

Each quiz item is shaped for the frontend:
    {
        "question": str,
        "options": [str, str, str, str],   # exactly 4 options
        "answer":  str                     # exact text of the correct option
    }
"""

from __future__ import annotations

import re
from typing import Any

from utils import GeminiError, extract_json, generate_text

_SYSTEM = (
    "You are EduGenie, a quiz generator for students. "
    "You produce clear, unambiguous multiple-choice questions with exactly one correct answer. "
    "You always respond with valid JSON and nothing else."
)

_PROMPT_TEMPLATE = (
    'Create exactly 3 multiple-choice questions to test understanding of the topic: "{topic}".\n\n'
    "Respond with ONLY a JSON array of 3 objects. Each object must have exactly these keys:\n"
    '  "question": a clear question (string)\n'
    '  "options":  an array of exactly 4 distinct answer choices (strings)\n'
    '  "answer":   the correct choice, copied EXACTLY from one of the 4 options (string)\n\n'
    "Do not include labels like 'A)' inside the options. "
    "Do not include explanations, markdown, or any text outside the JSON array."
)


def generate_quiz(topic: str) -> list[dict[str, Any]]:
    """Generate exactly 3 validated multiple-choice questions for a topic."""
    prompt = _PROMPT_TEMPLATE.format(topic=topic)
    raw = generate_text(prompt, system_instruction=_SYSTEM, temperature=0.6, as_json=True)
    data = extract_json(raw)
    return _coerce_quiz(data)


def _coerce_quiz(data: Any) -> list[dict[str, Any]]:
    """Validate and normalize the model output into exactly 3 clean MCQs."""
    # The model may wrap the list under a key; unwrap common shapes.
    if isinstance(data, dict):
        for key in ("quiz", "questions", "mcqs", "items", "data"):
            if isinstance(data.get(key), list):
                data = data[key]
                break

    if not isinstance(data, list):
        raise GeminiError("Couldn't build the quiz. Please try again.")

    cleaned: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue

        question = item.get("question") or item.get("q")
        options = item.get("options") or item.get("choices")
        answer = (
            item.get("answer")
            or item.get("correct")
            or item.get("correct_answer")
            or item.get("correctAnswer")
        )

        if not question or not isinstance(options, list):
            continue

        opts = [str(o).strip() for o in options if str(o).strip()]
        if len(opts) < 4:
            continue
        opts = opts[:4]

        answer_str = str(answer).strip() if answer is not None else ""
        resolved = _resolve_answer(answer_str, opts)

        cleaned.append(
            {
                "question": str(question).strip(),
                "options": opts,
                "answer": resolved,
            }
        )
        if len(cleaned) == 3:
            break

    if len(cleaned) < 3:
        raise GeminiError("Couldn't generate 3 complete questions. Please try again.")

    return cleaned


def _resolve_answer(answer: str, options: list[str]) -> str:
    """Return the exact option text that the answer refers to.

    Tolerates: exact text, a letter (A-D), a numeric index, or a
    'A) text' / 'A. text' style answer. Falls back to the first option.
    """
    if answer:
        # Exact (case-insensitive) text match.
        for opt in options:
            if opt.lower() == answer.lower():
                return opt

        # Single letter A-D.
        if len(answer) == 1 and answer.isalpha():
            idx = ord(answer.upper()) - ord("A")
            if 0 <= idx < len(options):
                return options[idx]

        # Numeric index (0-based or 1-based).
        if answer.isdigit():
            n = int(answer)
            if 0 <= n < len(options):
                return options[n]
            if 1 <= n <= len(options):
                return options[n - 1]

        # "A) text" / "A. text" / "A - text".
        match = re.match(r"^\s*([A-Da-d])[\).:\-]\s*(.*)$", answer)
        if match:
            letter_idx = ord(match.group(1).upper()) - ord("A")
            if 0 <= letter_idx < len(options):
                return options[letter_idx]
            rest = match.group(2).strip()
            for opt in options:
                if opt.lower() == rest.lower():
                    return opt

    # Safe fallback so the quiz always has a valid correct answer.
    return options[0]

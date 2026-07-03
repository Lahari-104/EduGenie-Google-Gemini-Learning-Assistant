"""
explanation_module.py — Concept Explanation.

Exposes explain_topic(topic) -> str
"""

from __future__ import annotations

from utils import generate_text

_SYSTEM = (
    "You are EduGenie, an educational assistant that explains concepts to complete beginners. "
    "Use simple language, short sentences, and a relatable analogy or example. "
    "Assume no prior knowledge. Keep the explanation focused and easy to follow."
)


def explain_topic(topic: str) -> str:
    """Return a beginner-friendly explanation of the given topic."""
    prompt = (
        "Explain the following topic to a beginner in a clear, structured way. "
        "Start with a one-line definition, then explain the key ideas, and finish "
        "with a simple example or analogy.\n\n"
        f"Topic: {topic}"
    )
    return generate_text(prompt, system_instruction=_SYSTEM, temperature=0.5)

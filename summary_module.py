"""
summary_module.py — Text Summarization.

Exposes summarize_text(text) -> str
"""

from __future__ import annotations

from utils import generate_text

_SYSTEM = (
    "You are EduGenie, an educational assistant that summarizes study material. "
    "Capture the key points faithfully and concisely. Do not invent information "
    "that is not present in the source text."
)


def summarize_text(text: str) -> str:
    """Return a concise summary of the provided educational text."""
    prompt = (
        "Summarize the following text for a student. Keep the main ideas and key "
        "points, and present them clearly.\n\n"
        "Text:\n"
        f"{text}"
    )
    return generate_text(prompt, system_instruction=_SYSTEM, temperature=0.3)

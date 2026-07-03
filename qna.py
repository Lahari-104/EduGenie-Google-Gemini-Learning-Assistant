"""
qna.py — Question Answering.

Exposes ask_question(question) -> str
"""

from __future__ import annotations

from utils import generate_text

_SYSTEM = (
    "You are EduGenie, a friendly and knowledgeable educational assistant. "
    "Answer the student's question clearly, accurately, and concisely. "
    "Use plain language, and include a short example only when it aids understanding. "
    "If the question is ambiguous, answer the most likely intended meaning."
)


def ask_question(question: str) -> str:
    """Return an AI-generated answer to a student's question."""
    prompt = (
        "Answer the following student question.\n\n"
        f"Question: {question}\n\n"
        "Answer:"
    )
    return generate_text(prompt, system_instruction=_SYSTEM, temperature=0.4)

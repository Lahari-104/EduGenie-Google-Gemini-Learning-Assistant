"""
utils.py — shared utilities for EduGenie.

Responsibilities:
  * Initialize the Google Gen AI (Gemini) client exactly once.
  * Read configuration (API key, model name) from the environment.
  * Provide a reusable text-generation helper with graceful error handling.
  * Safely extract JSON from model output.
  * Read and write request history to data/history.json.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import os
from dotenv import load_dotenv

from google import genai
from google.genai import types

# Load variables from a local .env file if present.
load_dotenv()

logger = logging.getLogger("edugenie")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_MODEL = "gemini-2.5-flash"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
HISTORY_FILE = DATA_DIR / "history.json"
MAX_HISTORY_ENTRIES = 1000

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class GeminiError(Exception):
    """Raised when the AI service is misconfigured or fails to respond.

    The message is safe to surface directly to the end user.
    """


# ---------------------------------------------------------------------------
# Client (created once, lazily, and thread-safely)
# ---------------------------------------------------------------------------
_client: Optional[genai.Client] = None
_client_lock = threading.Lock()
_history_lock = threading.Lock()


def get_model_name() -> str:
    """Return the configured Gemini model, defaulting to gemini-2.5-flash."""
    model = os.getenv("GEMINI_MODEL", "").strip()
    return model or DEFAULT_MODEL


def get_client() -> genai.Client:
    """Return a singleton Gemini client, creating it on first use."""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                api_key = os.getenv("GEMINI_API_KEY", "").strip()
                if not api_key:
                    raise GeminiError(
                        "GEMINI_API_KEY is not set. Add it to your .env file and restart the server."
                    )
                try:
                    _client = genai.Client(api_key=api_key)
                except Exception as exc:  # noqa: BLE001 - surface a clean message
                    logger.exception("Failed to initialize Gemini client")
                    raise GeminiError(
                        "Could not initialize the AI client. Check your API key and try again."
                    ) from exc
    return _client


# ---------------------------------------------------------------------------
# Text generation
# ---------------------------------------------------------------------------
def generate_text(
    prompt: str,
    *,
    system_instruction: Optional[str] = None,
    temperature: float = 0.6,
    as_json: bool = False,
) -> str:
    """Call Gemini with a prompt and return the response text.

    Raises GeminiError (with a user-safe message) on any failure.
    """
    client = get_client()

    config_kwargs: dict[str, Any] = {"temperature": temperature}
    if system_instruction:
        config_kwargs["system_instruction"] = system_instruction
    if as_json:
        config_kwargs["response_mime_type"] = "application/json"

    try:
        response = client.models.generate_content(
            model=get_model_name(),
            contents=prompt,
            config=types.GenerateContentConfig(**config_kwargs),
        )
    except Exception as exc:  # noqa: BLE001 - network / API / quota errors
        logger.exception("Gemini request failed")
        raise GeminiError(
            "The AI service is unavailable right now. Please try again in a moment."
        ) from exc

    text = getattr(response, "text", None)
    if not text or not text.strip():
        raise GeminiError("The AI service returned an empty response. Please try again.")
    return text.strip()


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------
def extract_json(raw: str) -> Any:
    """Parse JSON from a model response, tolerating markdown code fences."""
    if raw is None:
        raise GeminiError("The AI response was empty. Please try again.")

    text = raw.strip()

    # Strip surrounding ``` or ```json fences if present.
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text[:4].lower() == "json":
            text = text[4:].strip()

    # Direct parse.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fall back to the first balanced-looking array or object substring.
    for open_ch, close_ch in (("[", "]"), ("{", "}")):
        start = text.find(open_ch)
        end = text.rfind(close_ch)
        if start != -1 and end != -1 and end > start:
            snippet = text[start : end + 1]
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                continue

    raise GeminiError("The AI returned a response that wasn't valid JSON. Please try again.")


# ---------------------------------------------------------------------------
# History storage (JSON file)
# ---------------------------------------------------------------------------
def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not HISTORY_FILE.exists():
        HISTORY_FILE.write_text("[]", encoding="utf-8")


def load_history() -> list[dict[str, Any]]:
    """Return the stored history list; return an empty list on any problem."""
    try:
        _ensure_data_dir()
        content = HISTORY_FILE.read_text(encoding="utf-8").strip()
        if not content:
            return []
        data = json.loads(content)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        logger.warning("Could not read history file; starting fresh.")
        return []


def save_history(entries: list[dict[str, Any]]) -> None:
    """Persist the full history list to disk."""
    _ensure_data_dir()
    trimmed = entries[-MAX_HISTORY_ENTRIES:]
    HISTORY_FILE.write_text(
        json.dumps(trimmed, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def record_history(kind: str, request_input: Any, output: Any) -> None:
    """Append one interaction to history. Never raises (logging must not break requests)."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": kind,
        "input": request_input,
        "output": output,
    }
    try:
        with _history_lock:
            history = load_history()
            history.append(entry)
            save_history(history)
    except Exception:  # noqa: BLE001 - history failures must not break the API
        logger.exception("Failed to write history entry")

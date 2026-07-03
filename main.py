"""
main.py — EduGenie FastAPI application.

Run with:
    uvicorn main:app --reload

Endpoints (matched exactly to the frontend):
    GET  /                        -> serves the single-page UI
    GET  /qa?question=...         -> {"answer": str}
    POST /explain      {topic}    -> {"explanation": str}
    POST /quiz         {topic}    -> {"quiz": [ {question, options, answer} x3 ]}
    POST /summarize    {text}     -> {"summary": str}
    POST /learn/recommendations {topic} -> {"beginner": [...], "intermediate": [...], "advanced": [...]}
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, field_validator

import utils
from qna import ask_question
from explanation_module import explain_topic
from quiz_module import generate_quiz
from summary_module import summarize_text
from learning_path import generate_learning_path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("edugenie")

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="EduGenie", description="Gemini powered learning assistant", version="1.0.0")

# Static assets and templates.
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Input limits (characters).
MAX_SHORT_INPUT = 2000
MAX_LONG_INPUT = 20000


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
class TopicRequest(BaseModel):
    topic: str

    @field_validator("topic")
    @classmethod
    def _validate_topic(cls, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise ValueError("Enter a topic first.")
        if len(value) > MAX_SHORT_INPUT:
            raise ValueError(f"Topic is too long (max {MAX_SHORT_INPUT} characters).")
        return value


class TextRequest(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def _validate_text(cls, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise ValueError("Enter some text to summarize.")
        if len(value) > MAX_LONG_INPUT:
            raise ValueError(f"Text is too long (max {MAX_LONG_INPUT} characters).")
        return value


# ---------------------------------------------------------------------------
# Exception handling — return a clean string `detail` for the frontend
# ---------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Collapse FastAPI's validation error list into a single friendly message."""
    message = "Invalid request."
    errors = exc.errors()
    if errors:
        raw = errors[0].get("msg", message)
        message = raw.replace("Value error, ", "").strip() or message
    return JSONResponse(status_code=422, content={"detail": message})


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the single-page EduGenie UI."""
    return templates.TemplateResponse(request, "index.html")


@app.get("/qa")
async def qa_endpoint(question: str = Query(..., description="The student's question")):
    """Answer a student's question. Frontend: GET /qa?question=..."""
    q = (question or "").strip()
    if not q:
        raise HTTPException(status_code=422, detail="Enter a question first.")
    if len(q) > MAX_SHORT_INPUT:
        raise HTTPException(
            status_code=422, detail=f"Question is too long (max {MAX_SHORT_INPUT} characters)."
        )
    try:
        answer = ask_question(q)
    except utils.GeminiError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:  # noqa: BLE001
        logger.exception("Unexpected error in /qa")
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")

    utils.record_history("qa", q, answer)
    return {"answer": answer}


@app.post("/explain")
async def explain_endpoint(payload: TopicRequest):
    """Explain a concept. Frontend: POST /explain {topic}."""
    try:
        explanation = explain_topic(payload.topic)
    except utils.GeminiError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:  # noqa: BLE001
        logger.exception("Unexpected error in /explain")
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")

    utils.record_history("explain", payload.topic, explanation)
    return {"explanation": explanation}


@app.post("/quiz")
async def quiz_endpoint(payload: TopicRequest):
    """Generate a 3-question quiz. Frontend: POST /quiz {topic}."""
    try:
        quiz = generate_quiz(payload.topic)
    except utils.GeminiError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:  # noqa: BLE001
        logger.exception("Unexpected error in /quiz")
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")

    utils.record_history("quiz", payload.topic, quiz)
    return {"quiz": quiz}


@app.post("/summarize")
async def summarize_endpoint(payload: TextRequest):
    """Summarize text. Frontend: POST /summarize {text}."""
    try:
        summary = summarize_text(payload.text)
    except utils.GeminiError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:  # noqa: BLE001
        logger.exception("Unexpected error in /summarize")
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")

    utils.record_history("summarize", payload.text, summary)
    return {"summary": summary}


@app.post("/learn/recommendations")
async def learn_endpoint(payload: TopicRequest):
    """Recommend a learning path. Frontend: POST /learn/recommendations {topic}."""
    try:
        path = generate_learning_path(payload.topic)
    except utils.GeminiError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:  # noqa: BLE001
        logger.exception("Unexpected error in /learn/recommendations")
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")

    utils.record_history("learn", payload.topic, path)
    # Keys match the frontend renderer: beginner / intermediate / advanced.
    return path

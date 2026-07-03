# EduGenie — Google Gemini Powered Learning Assistant

EduGenie is an AI-powered study companion built with **FastAPI** and the **Google Gemini** API. It offers five independent tools on a single responsive page:

1. **Question answering** — ask a direct question, get a clear answer.
2. **Concept explanation** — beginner-friendly breakdowns of any topic.
3. **Quiz generator** — exactly 3 interactive multiple-choice questions.
4. **Text summarizer** — condense long study material into key points.
5. **Learning recommendations** — a beginner → advanced roadmap with resources.

The frontend is plain HTML/CSS/JavaScript (no framework); the backend is FastAPI serving JSON. Request history is stored in a flat JSON file — no database required.

---

## Tech stack

- Python 3.10+
- FastAPI + Uvicorn
- Google Gen AI SDK (`google-genai`), model **gemini-2.5-flash** (configurable)
- Jinja2 templates
- HTML5 / CSS3 / Vanilla JavaScript
- JSON file storage (`data/history.json`)

---

## Project structure

```
EduGenie/
├── main.py                 # FastAPI app + routes
├── utils.py                # Gemini client, helpers, history I/O
├── qna.py                  # ask_question()
├── explanation_module.py   # explain_topic()
├── quiz_module.py          # generate_quiz()
├── summary_module.py       # summarize_text()
├── learning_path.py        # generate_learning_path()
├── requirements.txt
├── README.md
├── .env.example
├── templates/
│   └── index.html
├── static/
│   ├── style.css
│   └── script.js
├── data/
│   └── history.json        # starts as []
└── assets/
```

---

## Setup

### 1. Create and activate a virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure your API key

Copy the example env file and add your key:

```bash
# Windows
copy .env.example .env
# macOS / Linux
cp .env.example .env
```

Then edit `.env`:

```
GEMINI_API_KEY=your_actual_key_here
GEMINI_MODEL=gemini-2.5-flash
```

Get a free API key at <https://aistudio.google.com/app/apikey>.

### 4. Run the server

```bash
uvicorn main:app --reload
```

Open <http://127.0.0.1:8000> in your browser.

---

## API reference

| Method | Path | Request | Response |
|--------|------|---------|----------|
| GET  | `/` | — | HTML page |
| GET  | `/qa?question=...` | query param | `{ "answer": "..." }` |
| POST | `/explain` | `{ "topic": "..." }` | `{ "explanation": "..." }` |
| POST | `/quiz` | `{ "topic": "..." }` | `{ "quiz": [ {question, options[4], answer} x3 ] }` |
| POST | `/summarize` | `{ "text": "..." }` | `{ "summary": "..." }` |
| POST | `/learn/recommendations` | `{ "topic": "..." }` | `{ "beginner": [...], "intermediate": [...], "advanced": [...] }` |

Errors return `{ "detail": "message" }` with an appropriate status code (422 for invalid input, 503 when the AI service is unavailable).

---

## Notes

- **Model configuration:** set `GEMINI_MODEL` in `.env` to use a different Gemini model; it defaults to `gemini-2.5-flash`.
- **History storage:** every successful request is appended to `data/history.json` as `{timestamp, type, input, output}`. The file keeps the most recent 1000 entries. This uses simple file locking suitable for a single-process dev server; for high-concurrency production use, migrate to a database.
- **No API key?** The page still loads, but each tool will return a clear "GEMINI_API_KEY is not set" message until you configure one.

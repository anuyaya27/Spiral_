# Spiral Backend

FastAPI backend for uploading chat exports, normalizing messages, and generating structured mixed-signals reports with the OpenAI API.

## Tech Stack
- Python 3.11+
- FastAPI + Pydantic v2
- SQLAlchemy 2.0 + Alembic
- SQLite by default (`app.db`)
- Optional PostgreSQL via `DATABASE_URL`
- OpenAI Python SDK
- Pytest

## Workflow
1. Upload a chat file (`.txt` or `.json`).
2. User explicitly clicks `Analyze texts`.
3. Backend calls OpenAI and returns a structured report.

## Core Endpoints
- `POST /uploads`
  - Stores parsed/encrypted chat messages
  - Returns `{ "upload_id": "...", "message_count": N }`
- `POST /uploads/{upload_id}/analyze`
  - Runs OpenAI analysis only when called
  - Returns report schema directly
- `GET /reports/{upload_id}`
  - Returns latest report for upload

Static frontend compatibility endpoints:
- `POST /compat/upload`
- `POST /compat/uploads/{upload_id}/analyze`
- `GET /compat/reports/{upload_id}`

## Report Schema
```json
{
  "mixed_signal_index": 0,
  "confidence": 0.0,
  "summary": "",
  "timeline": [
    {
      "timestamp": "2026-01-01T00:00:00Z",
      "message": "",
      "tags": ["HIGH ENERGY"],
      "type": "mixed"
    }
  ],
  "stats": {
    "initiation_percent": 0,
    "reply_delay_ratio": 0,
    "red_flags": 0
  },
  "signals": [
    {
      "name": "Warm-cold cycles",
      "score": 0.0,
      "explanation": "",
      "evidence": [
        {"timestamp": "2026-01-01T00:00:00Z", "excerpt": "", "sender": ""}
      ]
    }
  ]
}
```

## Privacy and Safety
- Raw message content remains encrypted at rest (`messages.encrypted_text`).
- Raw text is not logged by analysis services.
- Long conversations use truncation:
  - older messages are compressed into a model-generated summary
  - most recent messages are kept verbatim for evidence fidelity

## Local Development
1. Create a virtual environment:
   - `python -m venv venv`
   - `venv\Scripts\activate` (Windows)
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Create env file:
   - `Copy-Item .env.example .env`
4. Set required env values:
   - `OPENAI_API_KEY`
   - Optional `OPENAI_MODEL` (default `gpt-4o-mini`)
   - `JWT_SECRET`
   - `ENCRYPTION_KEY`
5. Run migrations:
   - `alembic upgrade head`
6. Start server:
   - `uvicorn app.main:app --reload`
7. Open:
   - `http://127.0.0.1:8000/`
   - `http://127.0.0.1:8000/docs`

## Manual Test
1. Open the frontend.
2. Upload a chat export.
3. Click `Analyze texts`.
4. Verify badge, timeline, and stats update with live report data.

## Run Tests
- `pytest -q`

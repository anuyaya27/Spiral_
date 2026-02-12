# Mixed Signals Recognition Backend

Production-ready FastAPI backend for uploading chat exports, parsing/normalizing messages, running explainable mixed-signals analysis, and returning structured reports.

## Tech Stack
- Python 3.11+
- FastAPI + Pydantic v2
- SQLAlchemy 2.0 + Alembic
- PostgreSQL (runtime target) + Redis
- Celery workers for async analysis + retention cleanup
- Docker + docker-compose
- Pytest

## Core Capabilities
- Auth:
  - `POST /auth/register`
  - `POST /auth/login`
  - `GET /auth/me`
- Upload lifecycle:
  - `POST /uploads` (multipart)
  - `GET /uploads/{upload_id}`
  - `DELETE /uploads/{upload_id}`
- Async analysis jobs:
  - `POST /uploads/{upload_id}/analyze`
  - `GET /jobs/{job_id}`
- Reports:
  - `GET /reports/{upload_id}`
  - `GET /reports/{upload_id}/highlights`
  - `GET /reports/{upload_id}/download?format=json|pdf` (`pdf` returns clean 501 stub)
- Frontend compatibility adapters:
  - `POST /compat/upload`
  - `POST /compat/uploads/{upload_id}/analyze`
  - `GET /compat/jobs/{job_id}`
  - `GET /compat/reports/{upload_id}`

## Privacy and Security
- Raw message content is encrypted at rest with Fernet (`messages.encrypted_text`, `excerpts.encrypted_excerpt`).
- Structured logging filter redacts text-like fields.
- No raw message content is logged by service code.
- JWT auth, bcrypt password hashing.
- Strict upload validation:
  - extension by platform
  - content type whitelist
  - max file size (`MAX_UPLOAD_SIZE_MB`)
- Rate limiting middleware (`RATE_LIMIT_PER_MINUTE` per IP).
- Hard delete endpoint removes upload + derived artifacts.
- Retention cleanup task deletes data past `retention_until` (default 30 days after completed analysis).

## Supported Formats
1. WhatsApp `.txt` export
2. iMessage JSON
3. Generic JSON:
   ```json
   {
     "participants": ["A", "B"],
     "messages": [{"ts":"ISO8601","sender":"A","text":"..."}]
   }
   ```

### iMessage JSON Assumptions
- Root object with `participants` and `messages`.
- Each message supports:
  - timestamp in `ts`, `timestamp`, or `date`
  - sender in `sender` or `from`
  - `text` body
- Timestamp can be:
  - ISO 8601 string
  - unix epoch seconds
- Naive timestamps are interpreted in upload timezone.

## Analysis Outputs
- Timeline metrics:
  - messages/day + messages/week
  - response-time stats by participant
  - initiation counts
  - streaks
  - rolling engagement shifts
- Detectors (score 0-1 + explanation + evidence IDs):
  - initiation imbalance
  - response latency asymmetry
  - warm-cold cycles
  - boundary-setting language
  - unresolved future talk
  - affection vs distance contradiction
- Message-level features:
  - local sentiment (VADER)
  - affection/avoidance/hedge markers
- Mixed Signal Index:
  - explainable 0-100 score + confidence
  - weighted sub-score breakdown
- Moments of ambiguity:
  - timestamp window
  - label
  - detector triggers
  - real message snippets (never fabricated)

## Project Structure
```text
app/
  main.py
  core/
  db/
  models/
  routers/
  schemas/
  services/
  workers/
tests/
docker-compose.yml
Dockerfile
alembic.ini
```

## Local Development (Docker)
1. Copy env:
   - `cp .env.example .env`
2. Set secure secrets:
   - `JWT_SECRET`
   - `ENCRYPTION_KEY`
3. Start services:
   - `docker compose up --build`
4. Run migrations:
   - `docker compose exec api alembic upgrade head`
5. API docs:
   - `http://localhost:8000/docs`
6. Frontend:
   - `http://localhost:8000/`

## Local Development (without Docker)
1. Install deps:
   - `pip install -r requirements.txt`
2. Set env variables (or `.env`)
3. Run API:
   - `uvicorn app.main:app --reload`
4. Start Celery worker:
   - `celery -A app.workers.celery_app:celery_app worker --loglevel=INFO`
5. Optional beat scheduler:
   - `celery -A app.workers.celery_app:celery_app beat --loglevel=INFO`
6. Open frontend:
   - `http://localhost:8000/`

## Run Tests
- `pytest -q`

## End-to-End Flow
1. Register/login
2. Upload a chat export
3. Trigger analysis job
4. Poll job status
5. Fetch report and highlights
6. Delete upload to hard-delete all artifacts

## Static Frontend Integration
- The repository serves `app/static/index.html` directly at `GET /`.
- The page uses a minimal vanilla JS layer to call compat endpoints.
- API base behavior:
  - default: same-origin (empty `window.API_BASE`)
  - override: set `window.API_BASE = "http://localhost:8000"` before the integration script runs

## Notes
- Internal time normalization is UTC with timezone-aware datetimes.
- Parsing keeps the design extensible with parser modules under `app/services/parsing/`.
- Analysis modules are isolated under `app/services/analysis/` for easy detector extension.

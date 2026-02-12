# Mixed Signals Recognition Backend

FastAPI backend for uploading chat exports, parsing/normalizing messages, running mixed-signals analysis, and returning structured reports.

## Tech Stack
- Python 3.11+
- FastAPI + Pydantic v2
- SQLAlchemy 2.0 + Alembic
- SQLite by default (`app.db`)
- Optional PostgreSQL via `DATABASE_URL`
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
- Analysis jobs:
  - `POST /uploads/{upload_id}/analyze`
  - `GET /jobs/{job_id}`
- Reports:
  - `GET /reports/{upload_id}`
  - `GET /reports/{upload_id}/highlights`
  - `GET /reports/{upload_id}/download?format=json|pdf`
- Frontend compatibility adapters:
  - `POST /compat/upload`
  - `POST /compat/uploads/{upload_id}/analyze`
  - `GET /compat/jobs/{job_id}`
  - `GET /compat/reports/{upload_id}`

## Privacy and Security
- Raw message content is encrypted at rest with Fernet (`messages.encrypted_text`, `excerpts.encrypted_excerpt`).
- Structured logging filter redacts text-like fields.
- JWT auth, bcrypt password hashing.
- Upload validation: extension/content-type whitelist + max file size.
- Rate limiting middleware (`RATE_LIMIT_PER_MINUTE` per IP).
- Hard delete endpoint removes upload + derived artifacts.
- Retention cleanup logic deletes data past `retention_until`.

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
alembic.ini
```

## Local Development
1. Create a virtual environment:
   - Windows PowerShell: `python -m venv venv`
   - Activate: `venv\Scripts\activate`
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Create env file:
   - `Copy-Item .env.example .env`
4. Set secure values in `.env`:
   - `JWT_SECRET`
   - `ENCRYPTION_KEY`
5. Run migrations:
   - `alembic upgrade head`
6. Start API:
   - `uvicorn app.main:app --reload`
7. Open:
   - API docs: `http://127.0.0.1:8000/docs`
   - Frontend: `http://127.0.0.1:8000/`

## Database Configuration
Default development database:
- `DATABASE_URL="sqlite:///./app.db"`

Optional PostgreSQL:
- Example: `DATABASE_URL="postgresql+psycopg://user:password@127.0.0.1:5432/mixedsignals"`

## Background Execution
- Analysis jobs are dispatched with FastAPI `BackgroundTasks` in local mode.
- Retention cleanup can be run manually:
  - `make cleanup`

## Run Tests
- `pytest -q`

## End-to-End Flow
1. Register/login
2. Upload a chat export
3. Trigger analysis job
4. Poll job status
5. Fetch report/highlights
6. Delete upload to hard-delete artifacts

## Static Frontend Integration
- `GET /` serves `app/static/index.html`.
- Default API base is same-origin; override by setting `window.API_BASE` before script init.

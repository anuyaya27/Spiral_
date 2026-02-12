# Frontend-Backend Integration Notes

## Discovery Findings

### Backend framework
- FastAPI app in `app/main.py`
- SQLAlchemy + Alembic for persistence
- FastAPI background tasks for async analysis jobs (`app/workers/`)

### Existing auth approach
- JWT bearer auth via:
  - `POST /auth/register`
  - `POST /auth/login`
  - `GET /auth/me`
- Protected endpoints use `Authorization: Bearer <token>`

### Existing upload/analysis/report endpoints
- Upload:
  - `POST /uploads` (multipart)
  - Requires auth
  - Requires `platform` (`whatsapp|imessage|generic`) + optional `timezone_name`
  - Returns `{ "upload_id": "..." }`
- Analyze:
  - `POST /uploads/{upload_id}/analyze`
  - Requires auth
  - Returns `{ "job_id": "..." }`
- Job status:
  - `GET /jobs/{job_id}`
  - Requires auth
  - Returns ORM-backed job shape with `status` + `progress`
- Report:
  - `GET /reports/{upload_id}`
  - Requires auth
  - Returns rich report (`report_json`) + `mixed_signal_index` + `confidence`
  - Report internals are richer than the frontend’s needed summary shape

### Background work
- Background task `analyze_upload_job` processes analysis
- Job states: `queued|running|succeeded|failed`
- Retention cleanup can be triggered manually

### Dev run mode
- Local run uses `uvicorn` without container dependencies

## Mismatches vs Frontend Needs
- Frontend is static/no-JS currently and has no auth flow.
- Existing APIs require JWT and extra upload metadata.
- Frontend needs straightforward upload -> analyze -> poll -> report sequence.
- Frontend needs simplified report JSON:
  - `mixed_signal_index`, `confidence`, `timeline[]`, `stats{}`

## Planned Changes (Minimal)
- Add a small compat router with unauthenticated endpoints for this static page:
  - `POST /compat/upload`
  - `POST /compat/uploads/{upload_id}/analyze`
  - `GET /compat/jobs/{job_id}`
  - `GET /compat/reports/{upload_id}`
- Compat router will internally reuse existing models/services and keep original endpoints unchanged.
- Add `GET /` to serve static `app/static/index.html`.
- Move provided static frontend into `app/static/index.html` and inject minimal vanilla JS only:
  - hidden file input
  - upload-zone + CTA wiring
  - upload/analyze/poll/report flow
  - DOM patching for badge/timeline/stats
  - loading/error states
  - `window.API_BASE` config support
- Update README with exact run and access instructions for integrated frontend.

## Changes Implemented
- Added `app/routers/compat.py` with unauthenticated adapter endpoints for static frontend:
  - `POST /compat/upload` -> `{ upload_id }`
  - `POST /compat/uploads/{upload_id}/analyze` -> `{ job_id }`
  - `GET /compat/jobs/{job_id}` -> `{ job_id, status, progress, error }`
  - `GET /compat/reports/{upload_id}` -> frontend summary shape + `full_report`
- Kept existing authenticated API routes unchanged.
- Added frontend serving at `GET /` from `app/static/index.html`.
- Integrated static HTML with minimal vanilla JS:
  - hidden file input + click wiring from upload zone/CTA
  - upload -> analyze -> poll -> report flow
  - dashboard badge/timeline/stats populated from live API data
  - loading and error text states
  - `window.API_BASE` override support (defaults to same origin)

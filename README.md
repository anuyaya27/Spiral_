# Spiral Backend

Spiral is a behavioral signal extraction engine built on FastAPI that ingests raw chat exports, normalizes conversational data, and generates structured mixed-signal analysis reports using a hybrid statistical + LLM-driven inference pipeline.

The system is designed as an explainable conversation analytics framework — not a sentiment toy — with explicit scoring logic, encrypted storage, and reproducible report schemas.

---

## System Architecture

Spiral operates as a multi-stage processing pipeline:

1. **Ingestion Layer**
   - Accepts `.txt` and `.json` chat exports
   - Parses heterogeneous formats into a normalized message schema:
     ```json
     {
       "timestamp": "...",
       "sender": "...",
       "content": "...",
       "conversation_id": "..."
     }
     ```
   - Handles timezone normalization and chronological ordering
   - Deduplicates and sanitizes malformed entries

2. **Secure Persistence Layer**
   - SQLAlchemy 2.0 ORM
   - Messages encrypted at rest (`Fernet` symmetric encryption)
   - Separation of metadata and encrypted content
   - Alembic-managed schema migrations
   - SQLite (default) or PostgreSQL via `DATABASE_URL`

3. **Feature Engineering Layer**
   Extracts structured behavioral features including:
   - Initiation frequency and directional imbalance
   - Inter-message latency distributions
   - Reply-delay asymmetry ratios
   - Conversation gap clustering
   - Engagement volatility over rolling time windows
   - Boundary-language detection markers
   - Warm–cold oscillation detection via temporal segmentation

4. **LLM-Assisted Signal Inference**
   - Structured prompt schema
   - Deterministic JSON validation via Pydantic v2
   - Enforced response schema with bounded timeline length
   - Truncation strategy:
     - Older messages compressed into model-generated semantic summaries
     - Recent messages preserved verbatim for evidence integrity

5. **Report Generation**
   Produces a validated, explainable report object with:
   - Quantified Mixed Signal Index
   - Confidence estimation
   - Temporal event tagging
   - Evidence-backed signal breakdown

---

## Tech Stack

- Python 3.11+
- FastAPI
- Pydantic v2 (strict validation, max-length enforcement)
- SQLAlchemy 2.0
- Alembic migrations
- SQLite (default) / PostgreSQL
- OpenAI Python SDK
- Pytest
- Fernet encryption (cryptography)

---

## Core Endpoints

### Upload Conversation
`POST /uploads`

- Parses and encrypts chat messages
- Returns:
```json
{
  "upload_id": "...",
  "message_count": 1234
}
```

---

### Run Analysis
`POST /uploads/{upload_id}/analyze`

- Triggers full analysis pipeline
- Calls LLM only on explicit request
- Returns validated structured report

---

### Retrieve Report
`GET /reports/{upload_id}`

- Fetches most recent analysis artifact

---

### Compatibility Endpoints
- `POST /compat/upload`
- `POST /compat/uploads/{upload_id}/analyze`
- `GET /compat/reports/{upload_id}`

---

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
        {
          "timestamp": "2026-01-01T00:00:00Z",
          "excerpt": "",
          "sender": ""
        }
      ]
    }
  ]
}
```

---

## Mixed Signal Index (Conceptual Model)

The `mixed_signal_index` is derived from a weighted composite of:

- Initiation imbalance score  
- Response time asymmetry score  
- Engagement volatility metric  
- Detected boundary-language density  
- Temporal warmth divergence score  

All components are normalized and aggregated into a bounded index for interpretability.  

This index does **not** predict intent — it quantifies behavioral inconsistency.

---

## Privacy and Data Handling

- Message text encrypted at rest (`messages.encrypted_text`)
- No raw message logging
- No background model training on user data
- Truncation strategy prevents full historical exposure to external APIs
- Explicit user-triggered analysis only

---

## Local Development

1. Create environment:
   ```
   python -m venv venv
   venv\Scripts\activate
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create `.env`:
   ```
   Copy-Item .env.example .env
   ```

4. Set required variables:
   - `OPENAI_API_KEY`
   - `OPENAI_MODEL` (default `gpt-4o-mini`)
   - `JWT_SECRET`
   - `ENCRYPTION_KEY`
   - Optional `DATABASE_URL`

5. Run migrations:
   ```
   alembic upgrade head
   ```

6. Start server:
   ```
   uvicorn app.main:app --reload
   ```

7. Access:
   - `http://127.0.0.1:8000/`
   - `http://127.0.0.1:8000/docs`

---

## Testing

Run:
```
pytest -q
```

Includes:
- Schema validation tests
- Timeline length enforcement
- Encryption round-trip verification
- API endpoint integration tests

---

## Design Philosophy

Spiral is built as a structured behavioral analytics system.  

It does not attempt to “decide” how someone feels.  

It extracts measurable conversational patterns and presents them transparently, with evidence and confidence bounds.

The goal is clarity through structure.

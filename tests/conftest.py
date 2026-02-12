import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["AUTO_CREATE_TABLES"] = "true"
os.environ["ENCRYPTION_KEY"] = "aLxM0wHk0w0oVx3G9iYfn7lr5J2v3xH5cM8D6lQ1t2Q="
os.environ["OPENAI_API_KEY"] = "test-key"
os.environ["OPENAI_MODEL"] = "gpt-4o-mini"

from app.db.base import Base
from app.db.session import engine
from app.main import create_app


@pytest.fixture(autouse=True)
def mock_llm(monkeypatch):
    def _fake_analyze_chat_with_llm(messages):
        first = messages[0]
        return {
            "mixed_signal_index": 72,
            "confidence": 0.83,
            "summary": "Communication shows inconsistent warmth and follow-through. Several messages indicate mixed intent.",
            "timeline": [
                {
                    "timestamp": first["ts"].isoformat(),
                    "message": str(first["text"])[:120],
                    "tags": ["VIBE SHIFT", "MIXED SIGNAL"],
                    "type": "mixed",
                }
            ],
            "stats": {"initiation_percent": 43, "reply_delay_ratio": 4.1, "red_flags": 15},
            "signals": [
                {
                    "name": "Warm-cold cycles",
                    "score": 0.81,
                    "explanation": "Warm messages are followed by cool replies.",
                    "evidence": [
                        {
                            "timestamp": first["ts"].isoformat(),
                            "excerpt": str(first["text"])[:80],
                            "sender": str(first["sender"]),
                        }
                    ],
                }
            ],
        }

    monkeypatch.setattr("app.services.analysis.runner.analyze_chat_with_llm", _fake_analyze_chat_with_llm)


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    path = Path("test.db")
    if path.exists():
        path.unlink()


@pytest.fixture()
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["AUTO_CREATE_TABLES"] = "true"
os.environ["ENCRYPTION_KEY"] = "aLxM0wHk0w0oVx3G9iYfn7lr5J2v3xH5cM8D6lQ1t2Q="

from app.db.base import Base
from app.db.session import engine
from app.main import create_app


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

PYTHON ?= python

.PHONY: install run test migrate upgrade cleanup

install:
	$(PYTHON) -m pip install -r requirements.txt

run:
	uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

test:
	pytest -q

migrate:
	alembic revision --autogenerate -m "migration"

upgrade:
	alembic upgrade head

cleanup:
	python -c "from app.workers.tasks import retention_cleanup_job; print(retention_cleanup_job())"

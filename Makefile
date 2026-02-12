PYTHON ?= python

.PHONY: install run worker beat test migrate upgrade

install:
	$(PYTHON) -m pip install -r requirements.txt

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

worker:
	celery -A app.workers.celery_app:celery_app worker --loglevel=INFO

beat:
	celery -A app.workers.celery_app:celery_app beat --loglevel=INFO

test:
	pytest -q

migrate:
	alembic revision --autogenerate -m "migration"

upgrade:
	alembic upgrade head


.PHONY: help install migrate migrations createsuperuser server test test-coverage lint lint-fix clean qcluster

help:
	@echo "Available commands:"
	@echo "  make install          - Install dependencies with uv"
	@echo "  make migrate          - Run database migrations"
	@echo "  make migrations       - Create new migrations"
	@echo "  make createsuperuser  - Create Django superuser"
	@echo "  make server           - Start development server"
	@echo "  make qcluster         - Start Django Q2 cluster"
	@echo "  make test             - Run tests"
	@echo "  make test-coverage    - Run tests with coverage"
	@echo "  make lint             - Check code with ruff"
	@echo "  make lint-fix         - Fix code with ruff"
	@echo "  make clean            - Clean up generated files"

install:
	uv sync

migrate:
	uv run python manage.py migrate

migrations:
	uv run python manage.py makemigrations

createsuperuser:
	uv run python manage.py createsuperuser

server:
	uv run python manage.py runserver

qcluster:
	uv run python manage.py qcluster

test:
	uv run pytest

test-coverage:
	uv run pytest --cov --cov-report=html --cov-report=term

lint:
	uv run ruff check .

lint-fix:
	uv run ruff check --fix .
	uv run ruff format .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage

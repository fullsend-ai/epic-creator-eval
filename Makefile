.PHONY: help sync test lint format

help:
	@echo "make sync     — install/update dependencies"
	@echo "make test     — run pytest"
	@echo "make lint     — run ruff linter, format checker, and mypy"
	@echo "make format   — auto-format with ruff (run before pushing)"

sync:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src/

format:
	uv run ruff format .

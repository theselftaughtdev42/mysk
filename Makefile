.PHONY: install test lint typecheck format format-check pre-commit check

install:
	uv sync --all-groups

test:
	uv run pytest

lint:
	uv run ruff check .

typecheck:
	uv run pyrefly check

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

pre-commit:
	uv run pre-commit run --all-files

check: format-check lint typecheck test pre-commit

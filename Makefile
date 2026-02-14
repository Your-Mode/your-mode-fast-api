.PHONY: help install install-dev run test check fix clean dev-setup all add-pkg add-dev-pkg build health

help:  ## Show help
	@grep -E '^[.a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

init:  ## Install production dependencies
	uv pip install -e .

init-dev:  ## Install development dependencies
	uv pip install -U pip
	uv pip install -e ".[dev]"
	pre-commit install --overwrite

run:  ## Run development server
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:  ## Run tests
	uv run pytest

check:  ## Check code quality (lint + format check)
	uv run ruff check .
	uv run ruff format --check .

fix:  ## Fix code automatically
	uv run ruff check --fix .
	uv run ruff format .

format:  ## Format code only
	uv run ruff format .

clean:  ## Clean cache files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -delete 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true

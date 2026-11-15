#!/usr/bin/env bash
# Everything CI checks, runnable locally.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest -q
python3 scripts/check_public_safety.py

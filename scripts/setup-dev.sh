#!/usr/bin/env bash
# Project-local development setup. Makes no system-wide changes.
set -euo pipefail
cd "$(dirname "$0")/.."
command -v uv >/dev/null || { echo "uv is required: https://docs.astral.sh/uv/" >&2; exit 1; }
uv sync --locked
PRIV="${DIGIMAX_PRIVATE:-$HOME/.local/share/digimaxos-private}"
mkdir -p "$PRIV" && chmod 700 "$PRIV"
echo "private workspace: $PRIV (mode 700)"
uv run digimax env check

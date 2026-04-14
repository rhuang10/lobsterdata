#!/usr/bin/env bash
# format.sh  –  auto-format src/ and examples/
#
# tests/ is intentionally excluded – it is not part of the release.
#
# Tools run in order:
#   1. isort  – sort and group imports
#   2. black  – reformat code style
#   3. ruff   – lint and auto-fix remaining issues
#
# Usage:
#   ./format.sh

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

TARGETS="src/ examples/"

echo "==> isort $TARGETS"
uv run isort $TARGETS

echo "==> black $TARGETS"
uv run black $TARGETS

echo "==> ruff check --fix $TARGETS"
uv run ruff check --fix $TARGETS

echo ""
echo "✓ Formatting complete."

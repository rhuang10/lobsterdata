#!/usr/bin/env bash
# run_tests.sh  –  run the full unit-test suite
#
# Usage:
#   ./run_tests.sh            # all tests
#   ./run_tests.sh -k "name"  # filter by test name
#   ./run_tests.sh -v         # verbose output

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

echo "==> uv run pytest tests/ $*"
uv run pytest tests/ "$@"

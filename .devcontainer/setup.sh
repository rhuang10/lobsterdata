#!/usr/bin/env bash
# .devcontainer/setup.sh
#
# Run automatically when the dev container is created or rebuilt
# (postCreateCommand in devcontainer.json).
#
# Steps:
#   1. Configure SSH access for git push.
#   2. Install all Python dependencies (dev group + examples extra) via uv sync.
#   3. Write and register the git pre-push hook that runs format checks and
#      unit tests before every push.

set -euo pipefail

REPO_ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"

# ── 1. Sync Python environment ────────────────────────────────────────────────
echo "==> uv sync (dev + all extras)…"
uv sync --all-extras



echo ""
echo "==> Setup complete."
echo "    Format code  : ./format.sh"
echo "    Run tests    : ./run_tests.sh"

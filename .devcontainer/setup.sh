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

# ── 1. SSH access for git push ────────────────────────────────────────────────
#
# RECOMMENDED: SSH agent forwarding (default)
#   devcontainer.json mounts the host SSH agent socket at /ssh-agent and sets
#   SSH_AUTH_SOCK=/ssh-agent.  The private key never enters the container.
#   Nothing to do here – ssh/git will pick up SSH_AUTH_SOCK automatically.
#
# FALLBACK: copy keys from a host-mounted read-only directory
#   Only used when the agent socket is unavailable (e.g. CI, headless Docker).
#   To enable, mount your host ~/.ssh into the container as /tmp/host-ssh
#   (read-only) by adding this to devcontainer.json "mounts":
#
#     "source=${localEnv:HOME}/.ssh,target=/tmp/host-ssh,type=bind,readonly"
#
#   ⚠️  SECURITY DOWNSIDES of copying keys:
#     – The private key is written to the container filesystem in plain text.
#     – Anyone who can `docker exec` into the container gains access to the key.
#     – Exporting or committing the container image leaks the key permanently.
#     – Prefer SSH agent forwarding whenever possible.
#
if [[ -S "${SSH_AUTH_SOCK:-}" ]]; then
    echo "==> SSH agent socket detected at $SSH_AUTH_SOCK – no key copy needed."
    # Ensure github.com is in known_hosts so the first push doesn't prompt
    mkdir -p ~/.ssh && chmod 700 ~/.ssh
    ssh-keyscan -H github.com >> ~/.ssh/known_hosts 2>/dev/null
elif [[ -d /tmp/host-ssh ]]; then
    echo "==> SSH agent not available – copying keys from /tmp/host-ssh (fallback)."
    echo "    ⚠️  Private key will be present on the container filesystem."
    mkdir -p ~/.ssh && chmod 700 ~/.ssh
    # Copy key files; preserve permissions
    find /tmp/host-ssh -maxdepth 1 \( -name 'id_*' -o -name 'config' -o -name 'known_hosts' \) \
        -exec cp -p {} ~/.ssh/ \;
    # Private keys must be owner-read-only for ssh to accept them
    chmod 600 ~/.ssh/id_* 2>/dev/null || true
    chmod 644 ~/.ssh/config ~/.ssh/known_hosts 2>/dev/null || true
    # Add github.com to known_hosts if not already present
    ssh-keyscan -H github.com >> ~/.ssh/known_hosts 2>/dev/null
    echo "    SSH keys copied."
else
    echo "==> WARNING: No SSH agent socket and no host key mount found."
    echo "    git push over SSH will not work until you configure SSH access."
    echo "    See .devcontainer/devcontainer.json for options."
fi

# ── 2. Sync Python environment ────────────────────────────────────────────────
echo "==> uv sync (dev + all extras)…"
uv sync --all-extras

# ── 3. Register .githooks directory with git ──────────────────────────────────
echo "==> Registering .githooks with git…"
git -C "$REPO_ROOT" config core.hooksPath .githooks
chmod +x "$REPO_ROOT"/.githooks/*
echo "    pre-commit and pre-push hooks active from .githooks/"

echo ""
echo "==> Setup complete."
echo "    Format code  : ./format.sh"
echo "    Run tests    : ./run_tests.sh"

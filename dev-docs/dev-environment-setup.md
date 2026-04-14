# Development Environment Setup

This guide covers everything needed to go from a fresh clone to a fully
working dev container with `git push` over SSH.

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine on Linux)
- [VS Code](https://code.visualstudio.com/) with the
  [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

---

## 1 — Generate an SSH key (skip if you already have one)

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
# Accept the default path (~/.ssh/id_ed25519) and set a passphrase
```

Add the public key to GitHub:

```bash
cat ~/.ssh/id_ed25519.pub
# Copy the output → GitHub → Settings → SSH and GPG keys → New SSH key
```

---

## 2 — Configure SSH agent forwarding on the host

The dev container forwards your host SSH agent into the container so the
private key **never leaves the host**. You must have the agent running and
your key loaded before opening VS Code.

### macOS

`AddKeysToAgent yes` re-adds the key to the agent automatically on first use.
`UseKeychain yes` is **macOS-specific** — it stores the passphrase in the
macOS Keychain so you are never prompted again after a reboot.

Add the following to `~/.ssh/config` (create the file if it does not exist):

```
Host *
    AddKeysToAgent yes
    UseKeychain yes
    IdentityFile ~/.ssh/id_ed25519
```

Then load the key once:

```bash
ssh-add --apple-use-keychain ~/.ssh/id_ed25519
```

After this, the agent starts automatically on login and the key is re-added
from the Keychain — no further action needed on reboot.

### Linux

`UseKeychain yes` is **not supported** on Linux OpenSSH and will produce an
error if included. Use only `AddKeysToAgent yes`:

```
Host *
    AddKeysToAgent yes
    IdentityFile ~/.ssh/id_ed25519
```

The agent does not start automatically on all Linux setups. Add this to your
`~/.bashrc` or `~/.profile` so it starts on every shell session and the key
is loaded automatically:

```bash
# ~/.bashrc  (or ~/.profile for login shells)
if ! pgrep -u "$USER" ssh-agent > /dev/null 2>&1; then
    eval "$(ssh-agent -s)"
fi
ssh-add -q ~/.ssh/id_ed25519 2>/dev/null || true
```

Most desktop environments (GNOME, KDE) start their own SSH agent
automatically — in that case you only need the `ssh-add` line.

### Windows (WSL2)

Enable the built-in Windows OpenSSH Agent service **once** in an elevated
PowerShell:

```powershell
Set-Service ssh-agent -StartupType Automatic
Start-Service ssh-agent
ssh-add $env:USERPROFILE\.ssh\id_ed25519
```

Then bridge the Windows agent socket into WSL2. Install the required tools:

```bash
sudo apt install socat
# Download npiperelay.exe from https://github.com/jstarks/npiperelay/releases
# and place it somewhere on your Windows PATH (e.g. C:\Windows\System32)
```

Add to your WSL2 `~/.bashrc`:

```bash
export SSH_AUTH_SOCK=$HOME/.ssh/agent.sock
if ! ss -lt 2>/dev/null | grep -q "$SSH_AUTH_SOCK"; then
    rm -f "$SSH_AUTH_SOCK"
    (setsid socat UNIX-LISTEN:"$SSH_AUTH_SOCK",fork \
        EXEC:"npiperelay.exe -ei -s //./pipe/openssh-ssh-agent",nofork &)
fi
```

Restart your WSL2 shell, then verify:

```bash
ssh-add -l   # should list your key
```

---

## 3 — Verify the agent is loaded (all platforms)

```bash
ssh-add -l
# Expected: 256 SHA256:xxxx your_email@example.com (ED25519)
# If it says "no identities": re-run ssh-add ~/.ssh/id_ed25519
```

---

## 4 — Open the dev container

1. Open the repository folder in VS Code.
2. When prompted, click **Reopen in Container** (or run
   **Dev Containers: Reopen in Container** from the command palette).
3. VS Code builds the image and runs `.devcontainer/setup.sh`, which:
   - Detects the forwarded agent socket and adds `github.com` to `known_hosts`
   - Runs `uv sync --all-extras` to install all Python dependencies
   - Registers `.githooks/` with git (`core.hooksPath`)

---

## 5 — Verify git push works inside the container

```bash
ssh -T git@github.com
# Expected: Hi <username>! You've successfully authenticated...

git push
```

---

## 6 — API credentials

Copy the environment template and fill in your LOBSTER credentials:

```bash
cp .env.example .env
# Edit .env with your API key and secret
```

The `.env` file is git-ignored and is loaded automatically by both the
example scripts and the dev container.

---

## Day-to-day workflow

| Task | Command |
|---|---|
| Install / sync dependencies | `uv sync --all-extras` |
| Format code (`src/` and `examples/`) | `./format.sh` |
| Run tests | `./run_tests.sh` |
| Run a specific test | `./run_tests.sh -k test_name` |
| Interactive CLI | `uv run python examples/cli.py submit` |
| Bulk request | `uv run python examples/bulk_request.py --csv examples/nasdaq_100.csv --start-date YYYY-MM-DD --end-date YYYY-MM-DD` |

The `pre-commit` git hook enforces formatting on `src/` and `examples/`
automatically. The `pre-push` hook runs the full test suite before every push.
Run `./format.sh` and re-stage if a commit is blocked.

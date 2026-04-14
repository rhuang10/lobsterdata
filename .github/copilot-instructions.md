# Project Guidelines

## Build and Test

This project uses [uv](https://github.com/astral-sh/uv) as its package and environment manager.
Always run Python commands through `uv run` so the correct virtual environment and dependencies are used automatically.

| Instead of | Use |
|---|---|
| `python script.py` | `uv run python script.py` |
| `python -m pytest` | `uv run pytest` |
| `python -m black` | `uv run black` |
| `python -m isort` | `uv run isort` |
| `pip install <pkg>` | `uv add <pkg>` (runtime) or `uv add --dev <pkg>` (dev) |

Install all dependencies (including dev group and all extras):

```bash
uv sync --all-extras
```

Run the test suite:

```bash
uv run pytest tests/
```

Run formatters:

```bash
uv run black src/ tests/ examples/
uv run isort src/ tests/ examples/
```

Run an example script:

```bash
uv run python examples/cli.py submit
uv run python examples/bulk_request.py --csv examples/nasdaq_100.csv --start-date 2026-04-01 --end-date 2026-04-01
```

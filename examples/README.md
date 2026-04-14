# Examples

This directory contains runnable CLI scripts for the `lobsterdata` package.

| Script | What it does |
|---|---|
| [`cli.py`](#clipy) | Interactive CLI: `submit` one request or `download` ready data |
| [`bulk_request.py`](#bulk_requestpy) | Async bulk pipeline: submit many symbols from a CSV and stream-download results |

---

## Prerequisites

Install the package with the `examples` extra, which includes [`anyio`](https://anyio.readthedocs.io) and [`python-dotenv`](https://pypi.org/project/python-dotenv/):

```bash
pip install "lobsterdata[examples]"
```

Or, from the source tree with [uv](https://github.com/astral-sh/uv):

```bash
uv pip install -e ".[examples]"
```

---

## Credentials

Both scripts load credentials from a `.env` file automatically (via `python-dotenv`), falling back to environment variables. **They will exit with a clear error message if the credentials are not found.**

### Recommended: `.env` file

```bash
cp .env.example .env
```

Then open `.env` and fill in your values:

```dotenv
LOBSTER_API_KEY=your_api_key_here
LOBSTER_API_SECRET=your_api_secret_here
LOBSTER_IS_PILOT=true
```

> `.env` is listed in `.gitignore` and will never be committed.

### Alternative: export environment variables

```bash
export LOBSTER_API_KEY="your_api_key_here"
export LOBSTER_API_SECRET="your_api_secret_here"
export LOBSTER_IS_PILOT="true"   # true → pilot.lobsterdata.com, false → production
```

You can obtain your API key and secret from the [LOBSTER website](https://lobsterdata.com).

---

## cli.py

An interactive command-line tool with two subcommands.

### `submit` — submit a single request

Prompts for a ticker symbol, date range, order book level, and exchange. All inputs are validated against the API constraints before submission.

```bash
python examples/cli.py submit
```

Example session:

```
Connecting to LOBSTER API…
✓ Authenticated

=== Submit a new data request ===

Ticker symbol (e.g. AAPL): AAPL
Start date (YYYY-MM-DD): 2026-04-01
End date   (YYYY-MM-DD): 2026-04-01
Level (0 or 10) [10]:
Exchange [NASDAQ]:

Submitting: AAPL  2026-04-01→2026-04-01  level=10  exchange=NASDAQ
✓ Request submitted successfully – ID: 101
```

Input validation enforced by the script:

| Field | Constraint |
|---|---|
| Date format | Must be `YYYY-MM-DD` |
| Date range | `end_date ≥ start_date` and span ≤ 31 days |
| Level | Must be `0` or `10` |

### `download` — download ready data

Fetches the list of all finished requests and lets you pick one by ID, or download everything at once.

```bash
python examples/cli.py download
```

Example session:

```
=== Download ready data ===

Fetching list of downloadable requests…
ID         Symbol   Start        End          Size (MB)
---------------------------------------------------------
101        AAPL     2026-04-01   2026-04-01       14.72
102        MSFT     2026-04-01   2026-04-01       11.05

Enter a request ID to download, or "all" to download everything: all
Download directory [./downloads]:

Downloading ID 101…
  ✓ Saved: /workspaces/lobsterdata/downloads/AAPL_20260401_20260401_10.zip
Delete from server after download? (y/n) [y]:
  ✓ Deleted ID 101 from server
…
```

---

## bulk_request.py

An async bulk pipeline powered by [anyio](https://anyio.readthedocs.io) (asyncio backend). Two tasks run concurrently inside an `anyio` task group:

- **Submit task** — reads tickers from a CSV file and submits one request per symbol, sleeping 3 seconds between each call (rate-limit guard).
- **Download task** — polls `list_alive_requests` in the background; downloads and deletes each file from the server immediately as it becomes ready.

```bash
python examples/bulk_request.py \
    --csv examples/nasdaq_100.csv \
    --start-date 2026-04-01 \
    --end-date 2026-04-01
```

All available flags:

| Flag | Default | Description |
|---|---|---|
| `--csv` | *(required)* | Path to CSV file with a `Ticker` column |
| `--start-date` | *(required)* | Start date (`YYYY-MM-DD`) |
| `--end-date` | *(required)* | End date (`YYYY-MM-DD`, ≤ 31 days after start) |
| `--level` | `10` | Order book depth (`0` or `10`) |
| `--exchange` | `NASDAQ` | Exchange name |
| `--download-dir` | `./downloads` | Directory for downloaded files |
| `--poll-interval` | `30` | Seconds between readiness polls |
| `--submit-delay` | `3` | Seconds between successive submissions |

The CSV file must contain a `Ticker` column. Additional columns are ignored. See [`nasdaq_100.csv`](nasdaq_100.csv) for an example.

---

## API Quick Reference

```python
from lobsterdata import LobsterClient

client = LobsterClient(api_key="...", api_secret="...", is_pilot=True)

# Submit a new request
result = client.submit_request("AAPL", "2026-04-01", "2026-04-01", level=10)
request_id = result["data"]["request_id"]

# List all requests
requests = client.list_requests()

# List only requests ready to download
ready = client.list_downloadable_requests()

# Download a single request by ID
path = client.download_request(request_id=42, download_dir="./downloads")

# Download everything available and remove from server
paths = client.download_and_cleanup(download_dir="./downloads")

# Delete a request from the server
client.delete_request(request_id=42)
```

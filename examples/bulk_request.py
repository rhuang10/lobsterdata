"""
Bulk data request script for the lobsterdata package.

Reads a list of ticker symbols from a CSV file (must contain a "Ticker" column),
then concurrently:

  1. Submits one request per symbol (3-second pause between submissions to
     stay within the API rate limit of 20 req/min).
  2. Polls every POLL_INTERVAL seconds (default: 30) in a background async
     task; downloads and deletes each file from the server as soon as it
     becomes available.

Both tasks run inside an anyio task group on the **asyncio** backend.
Blocking HTTP calls are offloaded to a thread via ``anyio.to_thread.run_sync``
so the event loop is never stalled.

Credentials
-----------
Copy .env.example to .env and fill in your credentials:

    cp .env.example .env
    # then edit .env with your API key and secret

The script loads .env automatically. You can also export variables directly:

    export LOBSTER_API_KEY="your_api_key_here"
    export LOBSTER_API_SECRET="your_api_secret_here"
    export LOBSTER_IS_PILOT="true"

Usage
-----

    python examples/bulk_request.py \\
        --csv examples/nasdaq_100.csv \\
        --start-date 2026-04-01 \\
        --end-date 2026-04-01

Optional flags:

    --level          0 or 10 (default: 10)
    --exchange       Exchange name (default: NASDAQ)
    --download-dir   Where to save downloaded files (default: ./downloads)
    --poll-interval  Seconds between readiness checks (default: 30)
    --submit-delay   Seconds between successive submissions (default: 3)

Dependencies
------------
    pip install "lobsterdata[examples]"
"""

from __future__ import annotations

import argparse
import csv
import os
import re
from datetime import date
from pathlib import Path

import anyio
import anyio.to_thread
from dotenv import load_dotenv

from lobsterdata import LobsterClient

# ---------------------------------------------------------------------------
# Credentials — loaded from .env (if present) then environment variables
# ---------------------------------------------------------------------------
load_dotenv()  # no-op if .env does not exist

API_KEY = os.environ.get("LOBSTER_API_KEY")
API_SECRET = os.environ.get("LOBSTER_API_SECRET")

if not API_KEY or not API_SECRET:
    import sys

    sys.exit(
        "Error: LOBSTER_API_KEY and LOBSTER_API_SECRET must be set.\n"
        "Copy .env.example → .env and fill in your credentials, "
        "or export them as environment variables."
    )

IS_PILOT = os.environ.get("LOBSTER_IS_PILOT", "true").lower() == "true"

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_VALID_LEVELS = {0, 10}
_MAX_DATE_RANGE_DAYS = 31


# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------


def _parse_date(value: str) -> date:
    if not _DATE_RE.match(value):
        raise argparse.ArgumentTypeError(
            f"Invalid date '{value}'. Expected format: YYYY-MM-DD"
        )
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _parse_level(value: str) -> int:
    try:
        level = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Level must be an integer.") from exc
    if level not in _VALID_LEVELS:
        raise argparse.ArgumentTypeError(
            f"Invalid level {level}. Allowed values: {sorted(_VALID_LEVELS)}"
        )
    return level


def _load_symbols(csv_path: Path) -> list[str]:
    """Return a deduplicated, order-preserving list of tickers from a CSV."""
    seen: set[str] = set()
    symbols: list[str] = []
    with csv_path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or "Ticker" not in reader.fieldnames:
            raise ValueError(
                f"CSV file must contain a 'Ticker' column. "
                f"Found columns: {reader.fieldnames}"
            )
        for row in reader:
            ticker = row["Ticker"].strip().upper()
            if ticker and ticker not in seen:
                seen.add(ticker)
                symbols.append(ticker)
    return symbols


# ---------------------------------------------------------------------------
# Async tasks
# ---------------------------------------------------------------------------


async def submit_all(
    client: LobsterClient,
    symbols: list[str],
    start_date: str,
    end_date: str,
    level: int,
    exchange: str,
    submit_delay: float,
    submission_done: anyio.Event,
) -> None:
    """Submit one request per symbol, honouring the rate-limit delay."""
    print(f"[submit] Starting – {len(symbols)} symbol(s) to submit\n")

    for i, symbol in enumerate(symbols):
        result = await anyio.to_thread.run_sync(
            lambda s=symbol: client.submit_request(
                symbol=s,
                start_date=start_date,
                end_date=end_date,
                level=level,
                exchange=exchange,
            )
        )
        request_id = result.get("data", {}).get("request_id", "?")
        print(f"[submit] ({i + 1}/{len(symbols)}) {symbol} – ID: {request_id}")

        if i < len(symbols) - 1:
            await anyio.sleep(submit_delay)

    print(f"\n[submit] All {len(symbols)} request(s) submitted.\n")
    submission_done.set()


async def poll_and_download(
    client: LobsterClient,
    download_dir: str,
    poll_interval: float,
    submission_done: anyio.Event,
) -> None:
    """
    Poll list_alive_requests every poll_interval seconds.
    Download and delete each finished file immediately.
    Exit once all submissions are done and no alive requests remain.
    """
    print(f"[download] Background task started – polling every {poll_interval}s\n")

    while True:
        await anyio.sleep(poll_interval)

        alive: list[dict] = await anyio.to_thread.run_sync(client.list_alive_requests)

        if not alive:
            if submission_done.is_set():
                print("[download] No more alive requests – finishing.")
                break
            # Submissions still in progress; keep waiting
            print("[download] No alive requests yet – waiting for submissions…")
            continue

        pending_count = 0
        for req in alive:
            rid = str(req.get("request_id") or req.get("id"))
            status = req.get("status", "unknown")

            if (
                status == "finished"
                and req.get("request_data_size", 0) > 0
                and not req.get("request_file_deleted", False)
            ):
                size_mb = req.get("request_data_size", 0) / (1024 * 1024)
                print(f"[download] ID {rid} ready ({size_mb:.2f} MB) – downloading…")

                filepath = await anyio.to_thread.run_sync(
                    lambda r=rid: client.download_request(r, download_dir=download_dir)
                )
                print(f"[download]   ✓ Saved:   {filepath}")

                await anyio.to_thread.run_sync(lambda r=rid: client.delete_request(r))
                print(f"[download]   ✓ Deleted ID {rid} from server")

            elif status == "finished" and req.get("request_data_size", 0) == 0:
                print(f"[download] ID {rid} finished but empty – deleting.")
                await anyio.to_thread.run_sync(lambda r=rid: client.delete_request(r))
            else:
                pending_count += 1

        still_alive: list[dict] = await anyio.to_thread.run_sync(
            client.list_alive_requests
        )
        if still_alive:
            print(
                f"[download] {len(still_alive)} request(s) still pending – "
                f"next check in {poll_interval}s…"
            )
        elif submission_done.is_set():
            print("[download] No more alive requests – finishing.")
            break


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def async_main(args: argparse.Namespace) -> None:
    start_date: date = args.start_date
    end_date: date = args.end_date

    if end_date < start_date:
        raise SystemExit("Error: end-date must be on or after start-date.")

    span = (end_date - start_date).days
    if span > _MAX_DATE_RANGE_DAYS:
        raise SystemExit(
            f"Error: date range is {span} days, but the API allows at most "
            f"{_MAX_DATE_RANGE_DAYS} days per request."
        )

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(f"Error: CSV file not found: {csv_path}")

    symbols = _load_symbols(csv_path)
    if not symbols:
        raise SystemExit("Error: No valid tickers found in the CSV file.")

    print("Connecting to LOBSTER API…")
    client = LobsterClient(api_key=API_KEY, api_secret=API_SECRET, is_pilot=IS_PILOT)
    print("✓ Authenticated\n")

    print(
        f"Configuration:\n"
        f"  CSV file     : {csv_path}\n"
        f"  Symbols      : {len(symbols)} ticker(s)\n"
        f"  Date range   : {start_date} → {end_date}  ({span} day(s))\n"
        f"  Level        : {args.level}\n"
        f"  Exchange     : {args.exchange}\n"
        f"  Download dir : {args.download_dir}\n"
        f"  Poll interval: {args.poll_interval}s\n"
        f"  Submit delay : {args.submit_delay}s\n"
    )

    submission_done = anyio.Event()

    async with anyio.create_task_group() as tg:
        tg.start_soon(
            submit_all,
            client,
            symbols,
            str(start_date),
            str(end_date),
            args.level,
            args.exchange,
            float(args.submit_delay),
            submission_done,
        )
        tg.start_soon(
            poll_and_download,
            client,
            args.download_dir,
            float(args.poll_interval),
            submission_done,
        )

    print("\nAll done!")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Bulk LOBSTER data request: submit many symbols from a CSV file "
            "and stream-download results as they become ready."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--csv",
        required=True,
        metavar="FILE",
        help="Path to CSV file with a 'Ticker' column.",
    )
    parser.add_argument(
        "--start-date",
        required=True,
        type=_parse_date,
        metavar="YYYY-MM-DD",
        help="Start date for the data request.",
    )
    parser.add_argument(
        "--end-date",
        required=True,
        type=_parse_date,
        metavar="YYYY-MM-DD",
        help="End date for the data request (≤ 31 days after start-date).",
    )
    parser.add_argument(
        "--level",
        type=_parse_level,
        default=10,
        metavar="LEVEL",
        help="Order book depth level (0 or 10).",
    )
    parser.add_argument(
        "--exchange",
        default="NASDAQ",
        metavar="EXCHANGE",
        help="Exchange name.",
    )
    parser.add_argument(
        "--download-dir",
        default="./downloads",
        metavar="DIR",
        help="Directory for downloaded files.",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=30.0,
        metavar="SECONDS",
        help="Seconds between readiness polls.",
    )
    parser.add_argument(
        "--submit-delay",
        type=float,
        default=3.0,
        metavar="SECONDS",
        help="Seconds between successive submissions (rate-limit guard).",
    )

    args = parser.parse_args()
    anyio.run(async_main, args, backend="asyncio")


if __name__ == "__main__":
    main()

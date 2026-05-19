"""
Interactive CLI for the lobsterdata package.

Commands are available:

    submit    Prompt for a symbol, start_date, and end_date, then submit a
              single LOBSTER data request.

    download  List all requests that are ready to download and let you pick
              one by ID, or type "all" to download everything at once.

    ls        List all active requests (waiting, running, or ready to
              download) with their current status.

    cancel    List cancellable requests and cancel the one you choose.

    delete    List finished requests and delete the one you choose.

    help      Show available commands.

    quit      Exit the CLI.

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
    python examples/cli.py
"""

import os
import re
import sys
from datetime import date

from dotenv import load_dotenv

from lobsterdata import LobsterClient

# ---------------------------------------------------------------------------
# Credentials — loaded from .env (if present) then environment variables
# ---------------------------------------------------------------------------
load_dotenv()  # no-op if .env does not exist

API_KEY = os.environ.get("LOBSTER_API_KEY")
API_SECRET = os.environ.get("LOBSTER_API_SECRET")

if not API_KEY or not API_SECRET:
    sys.exit(
        "Error: LOBSTER_API_KEY and LOBSTER_API_SECRET must be set.\n"
        "Copy .env.example → .env and fill in your credentials, "
        "or export them as environment variables."
    )

IS_PILOT = os.environ.get("LOBSTER_IS_PILOT", "true").lower() == "true"

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_VALID_LEVELS = {0, 10}
_MAX_DATE_RANGE_DAYS = 31
_DEFAULT_DOWNLOAD_DIR = "./downloads"


# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------


def _prompt(prompt_text: str, default: str | None = None) -> str:
    """Read a non-empty line from stdin, optionally showing a default value."""
    hint = f" [{default}]" if default is not None else ""
    while True:
        value = input(f"{prompt_text}{hint}: ").strip()
        if not value and default is not None:
            return default
        if value:
            return value
        print("  Input cannot be empty. Please try again.")


def _prompt_date(prompt_text: str) -> date:
    """Prompt until the user enters a valid YYYY-MM-DD date."""
    while True:
        raw = _prompt(prompt_text)
        if not _DATE_RE.match(raw):
            print("  Invalid format. Please use YYYY-MM-DD.")
            continue
        try:
            return date.fromisoformat(raw)
        except ValueError:
            print("  Invalid date. Please try again.")


def _prompt_level() -> int:
    """Prompt until the user enters a valid order book level (0 or 10)."""
    while True:
        raw = _prompt("Level (0 or 10)", default="10")
        try:
            level = int(raw)
        except ValueError:
            print("  Level must be an integer.")
            continue
        if level not in _VALID_LEVELS:
            print(f"  Invalid level. Allowed values: {sorted(_VALID_LEVELS)}")
            continue
        return level


# ---------------------------------------------------------------------------
# Command: submit
# ---------------------------------------------------------------------------


def cmd_submit(client: LobsterClient) -> None:
    print("\n=== Submit a new data request ===\n")

    symbol = _prompt("Ticker symbol (e.g. AAPL)").upper()

    while True:
        start = _prompt_date("Start date (YYYY-MM-DD)")
        end = _prompt_date("End date   (YYYY-MM-DD)")

        if end < start:
            print("  End date must be on or after start date.")
            continue

        span = (end - start).days
        if span > _MAX_DATE_RANGE_DAYS:
            print(
                f"  Date range is {span} days, but the API allows at most "
                f"{_MAX_DATE_RANGE_DAYS} days per request."
            )
            continue

        break

    level = _prompt_level()
    exchange = _prompt("Exchange", default="NASDAQ").upper()

    print(f"\nSubmitting: {symbol}  {start}→{end}  level={level}  exchange={exchange}")
    result = client.submit_request(
        symbol=symbol,
        start_date=str(start),
        end_date=str(end),
        level=level,
        exchange=exchange,
    )

    request_id = result.get("data", {}).get("request_id")
    if request_id:
        print(f"\n✓ Request submitted successfully – ID: {request_id}")
    else:
        print(f"\n⚠ Unexpected response: {result}")


# ---------------------------------------------------------------------------
# Command: ls
# ---------------------------------------------------------------------------


def cmd_ls(client: LobsterClient) -> None:
    print("\n=== Active requests ===\n")
    print("Fetching request list…")

    requests_list = client.list_alive_requests()

    if not requests_list:
        print("No active requests found.")
        return

    col_w = {"id": 10, "symbol": 8, "start": 12, "end": 12, "status": 12, "size": 10}
    header = (
        f"{'ID':<{col_w['id']}} {'Symbol':<{col_w['symbol']}} "
        f"{'Start':<{col_w['start']}} {'End':<{col_w['end']}} "
        f"{'Status':<{col_w['status']}} {'Size (MB)':>{col_w['size']}}"
    )
    print(header)
    print("-" * len(header))
    for req in requests_list:
        rid = str(req.get("request_id") or req.get("id"))
        symbol = req.get("symbol", "N/A")
        start = req.get("start_date", "N/A")[:10]
        end = req.get("end_date", "N/A")[:10]
        status = req.get("status", "N/A")
        size_mb = req.get("request_data_size", 0) / (1024 * 1024)
        print(
            f"{rid:<{col_w['id']}} {symbol:<{col_w['symbol']}} "
            f"{start:<{col_w['start']}} {end:<{col_w['end']}} "
            f"{status:<{col_w['status']}} {size_mb:>{col_w['size']}.2f}"
        )
    print()


# ---------------------------------------------------------------------------
# Command: download
# ---------------------------------------------------------------------------


def cmd_download(client: LobsterClient) -> None:
    print("\n=== Download ready data ===\n")
    print("Fetching list of downloadable requests…")

    ready = client.list_downloadable_requests()

    if not ready:
        print("No requests are currently ready to download.")
        return

    # Display table
    col_w = {"id": 10, "symbol": 8, "start": 12, "end": 12, "size": 10}
    header = (
        f"{'ID':<{col_w['id']}} {'Symbol':<{col_w['symbol']}} "
        f"{'Start':<{col_w['start']}} {'End':<{col_w['end']}} "
        f"{'Size (MB)':>{col_w['size']}}"
    )
    print(header)
    print("-" * len(header))
    for req in ready:
        rid = str(req.get("request_id") or req.get("id"))
        symbol = req.get("symbol", "N/A")
        start = req.get("start_datetime", "N/A")[:10]
        end = req.get("end_datetime", "N/A")[:10]
        size_mb = req.get("request_data_size", 0) / (1024 * 1024)
        print(
            f"{rid:<{col_w['id']}} {symbol:<{col_w['symbol']}} "
            f"{start:<{col_w['start']}} {end:<{col_w['end']}} "
            f"{size_mb:>{col_w['size']}.2f}"
        )

    print()
    valid_ids = {str(req.get("request_id") or req.get("id")) for req in ready}
    while True:
        choice = _prompt(
            'Enter a request ID to download, or "all" to download everything'
        )
        if choice.lower() == "all":
            to_download = ready
            break
        if choice in valid_ids:
            to_download = [
                r for r in ready if str(r.get("request_id") or r.get("id")) == choice
            ]
            break
        print(f"  '{choice}' is not in the list. Please try again.")

    download_dir = _prompt("Download directory", default=_DEFAULT_DOWNLOAD_DIR)

    print()
    for req in to_download:
        rid = str(req.get("request_id") or req.get("id"))
        print(f"Downloading ID {rid}…")
        filepath = client.download_request(rid, download_dir=download_dir)
        print(f"  ✓ Saved: {filepath}")

        delete = _prompt(
            "Delete from server after download? (y/n)", default="y"
        ).lower()
        if delete == "y":
            client.delete_request(rid)
            print(f"  ✓ Deleted ID {rid} from server")

    print("\nDone!")


# ---------------------------------------------------------------------------
# Command: cancel
# ---------------------------------------------------------------------------


def cmd_cancel(client: LobsterClient) -> None:
    print("\n=== Cancel a request ===\n")
    print("Fetching cancellable requests…")

    all_requests = client.list_alive_requests()
    cancellable = [r for r in all_requests if r.get("status") in ["waiting", "running"]]

    if not cancellable:
        print(
            "No requests available to cancel (all are finished or already cancelled)."
        )
        return

    col_w = {"id": 10, "symbol": 8, "start": 12, "end": 12, "status": 12}
    header = (
        f"{'ID':<{col_w['id']}} {'Symbol':<{col_w['symbol']}} "
        f"{'Start':<{col_w['start']}} {'End':<{col_w['end']}} "
        f"{'Status':<{col_w['status']}}"
    )
    print(header)
    print("-" * len(header))
    for req in cancellable:
        rid = str(req.get("request_id") or req.get("id"))
        symbol = req.get("symbol", "N/A")
        start = req.get("start_datetime", "N/A")[:10]
        end = req.get("end_datetime", "N/A")[:10]
        status = req.get("status", "N/A")
        print(
            f"{rid:<{col_w['id']}} {symbol:<{col_w['symbol']}} "
            f"{start:<{col_w['start']}} {end:<{col_w['end']}} "
            f"{status:<{col_w['status']}}"
        )

    print()
    valid_ids = {str(req.get("request_id") or req.get("id")) for req in cancellable}
    while True:
        choice = _prompt("Enter a request ID to cancel")
        if choice in valid_ids:
            break
        print(f"  '{choice}' is not in the list. Please try again.")

    print(f"\nCancelling request {choice}…")
    try:
        client.cancel_request(choice)
        print(f"✓ Request {choice} cancelled successfully")
    except Exception as e:
        print(f"⚠ Error cancelling request: {e}")


# ---------------------------------------------------------------------------
# Command: delete
# ---------------------------------------------------------------------------


def cmd_delete(client: LobsterClient) -> None:
    print("\n=== Delete request output ===\n")
    print("Fetching finished requests…")

    all_requests = client.list_alive_requests()
    finished = [r for r in all_requests if r.get("status") == "finished"]

    if not finished:
        print("No finished requests available to delete.")
        return

    col_w = {"id": 10, "symbol": 8, "start": 12, "end": 12, "size": 10}
    header = (
        f"{'ID':<{col_w['id']}} {'Symbol':<{col_w['symbol']}} "
        f"{'Start':<{col_w['start']}} {'End':<{col_w['end']}} "
        f"{'Size (MB)':>{col_w['size']}}"
    )
    print(header)
    print("-" * len(header))
    for req in finished:
        rid = str(req.get("request_id") or req.get("id"))
        symbol = req.get("symbol", "N/A")
        start = req.get("start_datetime", "N/A")[:10]
        end = req.get("end_datetime", "N/A")[:10]
        size_mb = req.get("request_data_size", 0) / (1024 * 1024)
        print(
            f"{rid:<{col_w['id']}} {symbol:<{col_w['symbol']}} "
            f"{start:<{col_w['start']}} {end:<{col_w['end']}} "
            f"{size_mb:>{col_w['size']}.2f}"
        )

    print()
    valid_ids = {str(req.get("request_id") or req.get("id")) for req in finished}
    while True:
        choice = _prompt("Enter a request ID to delete")
        if choice in valid_ids:
            break
        print(f"  '{choice}' is not in the list. Please try again.")

    confirm = _prompt(f"Delete output for request {choice}? (y/n)", default="n")
    if confirm.lower() != "y":
        print("Cancelled.")
        return

    print(f"\nDeleting output for request {choice}…")
    try:
        client.delete_request(choice)
        print(f"✓ Output for request {choice} deleted successfully")
    except Exception as e:
        print(f"⚠ Error deleting request: {e}")


# ---------------------------------------------------------------------------
# Command: help
# ---------------------------------------------------------------------------


def cmd_help() -> None:
    print("""
Available commands:

  submit    Submit a new LOBSTER data request interactively
  ls        List all active requests (waiting, running, or ready to download)
  download  Download ready data from a finished request
  cancel    Cancel a request that is waiting or running
  delete    Delete output files from a finished request
  help      Show this help message
  quit      Exit the CLI
""")


def main() -> None:
    print("Connecting to LOBSTER API…")
    client = LobsterClient(api_key=API_KEY, api_secret=API_SECRET, is_pilot=IS_PILOT)
    print("✓ Authenticated\n")

    print("Type 'help' for available commands or 'quit' to exit.\n")

    commands = {
        "submit": cmd_submit,
        "ls": cmd_ls,
        "download": cmd_download,
        "cancel": cmd_cancel,
        "delete": cmd_delete,
        "help": cmd_help,
    }

    while True:
        try:
            cmd = _prompt("Command").lower().strip()

            if cmd == "quit":
                print("Goodbye!")
                break
            elif cmd in commands:
                if cmd == "help":
                    commands[cmd]()
                else:
                    commands[cmd](client)
            elif cmd == "":
                continue
            else:
                print(f"Unknown command '{cmd}'. Type 'help' for available commands.")
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\n⚠ Error: {e}\n")


if __name__ == "__main__":
    main()

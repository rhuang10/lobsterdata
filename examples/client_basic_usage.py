"""
Basic usage example for the lobsterdata package.

This script shows the most common workflow:
  1. Create a client (authenticates automatically)
  2. Submit requests for multiple symbols in a loop
  3. Poll every 30 seconds; download and delete each file as soon as it is ready

Usage
-----
Set your credentials as environment variables (or copy .env.example → .env):

    export LOBSTER_API_KEY="your_api_key_here"
    export LOBSTER_API_SECRET="your_api_secret_here"
    export LOBSTER_IS_PILOT="true"

Then run:

    python examples/client_basic_usage.py
"""

import os
import time

from lobsterdata import LobsterClient

# ---------------------------------------------------------------------------
# Credentials – read from environment variables so secrets stay out of code
# ---------------------------------------------------------------------------
API_KEY = os.environ.get("LOBSTER_API_KEY", "your_api_key_here")
API_SECRET = os.environ.get("LOBSTER_API_SECRET", "your_api_secret_here")

# Set IS_PILOT=True to use the dev/pilot endpoint (dev.lobsterdata.com)
IS_PILOT = os.environ.get("LOBSTER_IS_PILOT", "true").lower() == "true"

POLL_INTERVAL = 30  # seconds between status checks


def main() -> None:
    # ------------------------------------------------------------------
    # Step 1: Create the client – authentication happens automatically
    # ------------------------------------------------------------------
    print("Connecting to LOBSTER API...")
    client = LobsterClient(api_key=API_KEY, api_secret=API_SECRET, is_pilot=IS_PILOT)
    print("✓ Authenticated successfully\n")

    # ------------------------------------------------------------------
    # Step 2: Submit requests for all symbols
    # ------------------------------------------------------------------
    # SYMBOLS = ["AAPL", "GOOG", "AMZN", "NVDA", "MSFT", "TSLA"]
    SYMBOLS = []
    START_DATE = "2025-02-03"
    END_DATE = "2025-02-15"

    print("Submitting data requests...")
    request_ids: list[str] = []
    for symbol in SYMBOLS:
        result = client.submit_request(
            symbol=symbol,
            start_date=START_DATE,
            end_date=END_DATE,
            level=10,
            exchange="NASDAQ",
        )
        request_id = result.get("data", {}).get("request_id")
        request_ids.append(str(request_id))
        print(f"  ✓ {symbol} – ID: {request_id}")
        time.sleep(1)

    print(f"\n{len(request_ids)} request(s) submitted.")
    print(f"Polling every {POLL_INTERVAL}s until all data is ready...\n")
    # ------------------------------------------------------------------
    # Step 3: Poll all pending requests (new + pre-existing), download
    #         and delete each one as soon as it becomes ready
    # ------------------------------------------------------------------
    alive_ids = {
        str(r.get("request_id") or r.get("id")) for r in client.list_alive_requests()
    }

    while alive_ids:
        time.sleep(POLL_INTERVAL)
        for rid in alive_ids.copy():
            # Confirm the file is actually available before downloading
            req = client.get_request(rid)
            if (
                req
                and req.get("status", "waiting") == "finished"
                and req.get("request_data_size", 0) > 0
                and not req.get("request_file_deleted", False)
            ):
                size_mb = req.get("request_data_size", 0) / (1024 * 1024)
                print(f"  ✓ ID {rid} is ready  |  {size_mb:.2f} MB")

                filepath = client.download_request(rid, download_dir="./downloads")
                print(f"    ✓ Saved: {filepath}")

                client.delete_request(rid)
                print(f"    ✓ Deleted ID {rid} from server")
            else:
                status = req.get("status", "unknown") if req else "unknown"
                print(
                    f"  ⚠ ID {rid} is no longer pending but not downloadable (status: {status}) – skipping"
                )
        alive_ids = {
            str(r.get("request_id") or r.get("id"))
            for r in client.list_alive_requests()
        }

        print(
            f"  [waiting] {len(alive_ids)} request(s) still alive – checking again in {POLL_INTERVAL}s..."
        )

    print("\nDone!")


if __name__ == "__main__":
    main()

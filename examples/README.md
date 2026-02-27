# Examples

This directory contains runnable examples for the `lobsterdata` package.

## Prerequisites

Install the package and its dependencies:

```bash
pip install lobsterdata
```

Or, if you are working from the source tree with [uv](https://github.com/astral-sh/uv):

```bash
uv sync
```

## Credentials

The examples read your API credentials from environment variables so that secrets never end up in source code:

```bash
export LOBSTER_API_KEY="your_api_key_here"
export LOBSTER_API_SECRET="your_api_secret_here"
export LOBSTER_IS_PILOT="true"   # use dev.lobsterdata.com; set to "false" for production
```

You can obtain your API key and secret from the [LOBSTER website](https://lobsterdata.com).

---

## basic_usage.py

Demonstrates the full common workflow in one script:

1. **Authenticate** – creating a `LobsterClient` validates your credentials automatically.
2. **List** completed requests that are ready for download.
3. **Download & clean up** – fetches every available data file locally and deletes it from the server.
4. **Submit** a new data request.

```bash
python examples/basic_usage.py
```

Expected output:

```
Connecting to LOBSTER API...
✓ Authenticated successfully

Fetching completed requests...
✓ Found 2 completed request(s)

  • ID 42 | AAPL 2025-01-06 → 2025-01-10 | Level 10 | 12.34 MB
  • ID 43 | MSFT 2025-01-06 → 2025-01-10 | Level 10 | 9.87 MB

Downloading and cleaning up completed requests...
✓ Downloaded 2 file(s):
  • /workspaces/lobsterdata/downloads/AAPL_2025-01-06_2025-01-10_10.zip
  • /workspaces/lobsterdata/downloads/MSFT_2025-01-06_2025-01-10_10.zip

Submitting a new data request...
✓ Request submitted – ID: 44
  Processing may take a few minutes. Run this script again to download.
```

---

## API Quick Reference

```python
from lobsterdata import LobsterClient

client = LobsterClient(api_key="...", api_secret="...", is_pilot=True)

# List completed requests
requests = client.list_requests()

# Submit a new request
client.submit_request("AAPL", "2025-02-03", "2025-02-07", level=10)

# Download a single request by ID
path = client.download_request(request_id=42, download_dir="./downloads")

# Download everything available and remove from server
paths = client.download_and_cleanup(download_dir="./downloads")

# Delete a request from the server
client.delete_request(request_id=42)
```

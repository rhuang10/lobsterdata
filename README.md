# lobsterdata

<p align="center">
  <img src="images/logos/LOBSTERLogo_w350px.png" alt="LOBSTER Logo" width="350"/>
</p>

Python client for the [LOBSTER](https://lobsterdata.com) financial data API.

LOBSTER provides high-quality, tick-level order book data for NASDAQ-listed stocks, widely used in academic finance research.

## Installation

```bash
pip install lobsterdata
```

## Quick start

```python
from lobsterdata import LobsterClient

client = LobsterClient(
    api_key="your_api_key",
    api_secret="your_api_secret",
    is_pilot=False,   # True → dev.lobsterdata.com, False → lobsterdata.com
)

# Submit a data request
result = client.submit_request(
    symbol="AAPL",
    start_date="2025-02-03",
    end_date="2025-02-07",
    level=10,
    exchange="NASDAQ",
)
request_id = result["data"]["request_id"]

# Download when ready
filepath = client.download_request(request_id, download_dir="./downloads")

# Or download + delete everything that is ready in one call
saved = client.download_and_cleanup(download_dir="./downloads")
```

See the [`examples/`](examples/) directory for a complete polling workflow.

## API reference

| Method | Description |
|---|---|
| `submit_request(symbol, start_date, end_date, level, exchange)` | Submit a new data construction request |
| `list_requests()` | List all requests for the authenticated user |
| `get_request(request_id)` | Look up a single request by ID |
| `list_alive_requests()` | Requests with status `waiting`, `running`, or undeleted `finished` |
| `list_downloadable_requests()` | Finished requests with data available for download |
| `download_request(request_id, download_dir)` | Download a completed request's data file |
| `delete_request(request_id)` | Delete a request and its file from the server |
| `download_and_cleanup(download_dir)` | Download all available files then delete them from the server |

## Credentials

Set your credentials as environment variables (copy `.env.example` → `.env`):

```bash
export LOBSTER_API_KEY="your_api_key"
export LOBSTER_API_SECRET="your_api_secret"
export LOBSTER_IS_PILOT="false"
```

## License

MIT

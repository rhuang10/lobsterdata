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

> **🦞 Pilot phase** — The API is currently in **pilot** and access is by invitation only.
> If you are an active Lobsterian and would like to join, please send an email to
> [service@lobsterdata.com](mailto:service@lobsterdata.com) with your **name**, **institute**, and **email address**.
> Only active Lobsterians will be granted access.

```python
from lobsterdata import LobsterClient

client = LobsterClient(
    api_key="your_api_key",
    api_secret="your_api_secret",
    is_pilot=True,   # True → dev.lobsterdata.com, False → lobsterdata.com
)
```

### 1 — Submit a request

```python
result = client.submit_request(
    symbol="AAPL",
    start_date="2025-02-03",
    end_date="2025-02-07",
    level=10,
    exchange="NASDAQ",
)
request_id = result["data"]["request_id"]
print(f"Request submitted – ID: {request_id}")
```

> **Submitting in a loop?** Sleep at least **3 seconds between each call** on the pilot server to stay well within the [rate limit](#rate-limiting) of 20 requests per minute. Exceeding it will block your API key for 10 minutes.
>
> ```python
> import time
>
> for symbol in symbols:
>     client.submit_request(symbol, start_date, end_date)
>     time.sleep(3)   # avoid rate-limit block
> ```

> Construction typically takes a few minutes depending on the date range and symbol.

### 2 — Check if ready

List your requests and inspect their status and data size:

```python
requests = client.list_requests()
for req in requests:
    rid = req.get("request_id") or req.get("id")
    status = req.get("status")
    size_mb = req.get("request_data_size", 0) / (1024 * 1024)
    print(f"ID {rid} | {req.get('symbol')} | status: {status} | size: {size_mb:.2f} MB")
```

A request is ready to download when **`status == "finished"`** and **`request_data_size > 0`**.

> Construction typically takes a few minutes. Re-run the snippet above until your request meets both conditions.

### 3 — Download and clean up

```python
filepath = client.download_request(request_id, download_dir="./downloads")
print(f"Saved to: {filepath}")

client.delete_request(request_id)
print("Deleted from server.")
```

> See the [`examples/`](examples/) directory for a complete multi-symbol polling workflow.

## API limits & constraints

> ⚠️ Violating any of these constraints will result in a rejected request (`error=1`) or a temporary API key block.

### Request constraints

| Parameter | Allowed values | Notes |
|---|---|---|
| `level` | `0` or `10` | Any other value is rejected |
| `frequency_seconds` | `0` or `null` | Any other value is rejected |
| Date range | ≤ 31 days | `end_date − start_date` must not exceed 31 days |

### Rate limiting

| Limit | Consequence |
|---|---|
| **20 requests per minute** | Exceeding this blocks your API key for **10 minutes** |

### Storage limit

The pilot server has a storage limit of **200 GB of raw CSV data** (not the compressed zip size). If your total stored data on the server exceeds this quota, your API key will be **blocked** with the reason `"Storage breached"`. The block is lifted automatically once you delete enough files to drop below the limit — use `delete_request()` or `download_and_cleanup()` to free up space.

### Checking your block state

```python
state = client.get_block_state()
print(state)
# {"blocked": False, "block_reason": None, "unblock_time": None}
```

If `blocked` is `True`, the response will include `block_reason` and `unblock_time`.

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
| `get_block_state()` | Check whether your API key is currently blocked and why |

## Credentials

Set your credentials as environment variables (copy `.env.example` → `.env`):

```bash
export LOBSTER_API_KEY="your_api_key"
export LOBSTER_API_SECRET="your_api_secret"
export LOBSTER_IS_PILOT="false"
```

## License

MIT

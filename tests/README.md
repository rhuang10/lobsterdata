# Test Suite — `LobsterClient`

Unit tests for `lobsterdata.client.LobsterClient`.  
All HTTP calls are mocked with `unittest.mock` — no real network connection or API credentials are required to run the suite.

## Running the tests

```bash
uv run pytest tests/ -v
```

Or, if you are using an activated virtual environment:

```bash
pytest tests/ -v
```

---

## Test file

| File | Description |
|---|---|
| `test_client.py` | Full unit-test coverage for `LobsterClient` |

---

## Test classes and cases

### `TestInit` — Construction & authentication

| Test | Description |
|---|---|
| `test_pilot_base_url` | `is_pilot=True` sets `base_url` to `dev.lobsterdata.com` |
| `test_prod_base_url` | `is_pilot=False` sets `base_url` to `lobsterdata.com` |
| `test_access_token_stored` | Access token returned by the API is stored on the instance |
| `test_auth_called_with_correct_params` | `POST /api-key/validate` is called with `api_key` and `api_secret` as query params |
| `test_auth_http_error_raises` | An HTTP error during authentication propagates to the caller |

---

### `TestAuthHeaders` — Bearer token header

| Test | Description |
|---|---|
| `test_bearer_token_in_headers` | `_auth_headers` property returns `{"Authorization": "Bearer <token>"}` |

---

### `TestListRequests` — `list_requests()`

| Test | Description |
|---|---|
| `test_returns_data_list` | Parses and returns the `data` array from the API response |
| `test_empty_data_key` | Returns an empty list when `data` is `[]` |
| `test_calls_correct_url` | Calls `GET /request/list` with the auth header |

---

### `TestGetRequest` — `get_request(request_id)`

| Test | Description |
|---|---|
| `test_finds_by_request_id` | Returns the matching request dict when the ID exists |
| `test_returns_none_when_not_found` | Returns `None` when no request matches the ID |
| `test_accepts_string_id` | Works when `request_id` is passed as a string |

---

### `TestListAliveRequests` — `list_alive_requests()`

| Test | Description |
|---|---|
| `test_returns_waiting_running_and_undeleted_finished` | Returns requests with status `waiting`, `running`, or `finished` (not yet deleted) |
| `test_excludes_deleted_finished` | Excludes requests that are `finished` but have `request_file_deleted = True` |

---

### `TestListDownloadableRequests` — `list_downloadable_requests()`

| Test | Description |
|---|---|
| `test_only_nonzero_undeleted` | Returns only requests with `status = finished`, `request_data_size > 0`, and `request_file_deleted = False` |

---

### `TestSubmitRequest` — `submit_request(...)`

| Test | Description |
|---|---|
| `test_returns_parsed_json` | Returns the parsed JSON response including `request_id` |
| `test_calls_correct_url_and_payload` | Posts to `POST /request/add` with the correct JSON payload fields |

---

### `TestDownloadRequest` — `download_request(request_id, download_dir)`

| Test | Description |
|---|---|
| `test_saves_file_and_returns_path` | Saves the streamed content to disk and returns the absolute path |
| `test_fallback_filename_when_no_content_disposition` | Uses `lobster_request_<id>.zip` when no `Content-Disposition` header is present |
| `test_creates_download_dir` | Creates the target directory if it does not already exist |

---

### `TestDeleteRequest` — `delete_request(request_id)`

| Test | Description |
|---|---|
| `test_calls_delete_endpoint` | Calls `DELETE /request/<id>` with the auth header and returns the parsed response |
| `test_http_error_propagates` | HTTP errors from the server propagate to the caller |

---

### `TestDownloadAndCleanup` — `download_and_cleanup(download_dir)`

| Test | Description |
|---|---|
| `test_downloads_and_deletes_all_downloadable` | Downloads every downloadable request and deletes it from the server |
| `test_skips_404_silently` | Silently skips requests whose files return a 404 (recorded in DB but missing on disk) |

---

## Test data

A shared `SAMPLE_REQUESTS` fixture covers the key status combinations:

| ID | Symbol | Status | Data size | File deleted |
|----|--------|--------|-----------|--------------|
| 1 | AAPL | `finished` | 5 MB | No → **downloadable** |
| 2 | GOOG | `waiting` | 0 | No → alive, not downloadable |
| 3 | AMZN | `running` | 0 | No → alive, not downloadable |
| 4 | NVDA | `finished` | 10 MB | Yes → excluded from all filters |

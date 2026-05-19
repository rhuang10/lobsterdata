# LOBSTER Request API

This document describes the HTTP endpoints under **`/request`** used to submit LOBSTER data jobs, list them, download results, cancel in-flight work, delete delivered files, and check API-key block status.

It is intended for **external integrators** who already authenticate with an API key access token. It does **not** cover account or university administration APIs.

Replace **`{BASE_URL}`** with your environment’s LOBSTER API base URL (for example `https://api.example.com`).

---

## Authentication

All endpoints in this document except the internal worker callback require:

| Header | Value |
|--------|--------|
| `Authorization` | `Bearer <access_token>` |

The **access token** must be issued by **`POST /api-key/validate`** using your API key and secret. That token encodes your numeric **user id** in the JWT `sub` claim. Tokens issued through other login flows (for example university web login) are **not** accepted on these routes and receive **403 Forbidden**.

---

## Response envelope

Most JSON endpoints return a single object:

```json
{
  "error": 0,
  "data": { }
}
```

| Field | Type | Meaning |
|-------|------|---------|
| `error` | `0` or `1` | `0` = success; `1` = business-level failure (HTTP status is often still **200**) |
| `data` | object | Payload on success, or error details on failure |

Some failures use standard HTTP error responses (**401**, **403**, **404**, **409**, **410**) with a JSON `detail` field instead of this envelope.

---

## Request lifecycle (`status`)

| Status | Meaning |
|--------|---------|
| `waiting` | Queued; not yet processed |
| `running` | Being processed by the backend worker |
| `finished` | Processing complete; download may be available if files were produced |
| `failed` | Processing failed |
| `cancelling` | User asked to cancel; the backend worker removes per-request output, then sets the row to `deleted` in the shared database |
| `deleted` | Output removed (user delete or cancellation completed); row kept for audit |

---

## Endpoints

### Submit a request

**`POST {BASE_URL}/request/add`**

Creates a new LOBSTER data request. On success, HTTP **201** and `error: 0`. The `data` object includes the new row (see **Request record** below). On validation or policy rejection, HTTP **200** with `error: 1` and rejection details (same shape as the create body plus `reason`).

**Request body (JSON)**

| Field | Type | Required | Notes |
|-------|------|----------|--------|
| `symbol` | string | yes | Ticker, max 50 characters; stored uppercase |
| `start_date` | date (ISO `YYYY-MM-DD`) | yes | Inclusive |
| `end_date` | date (ISO `YYYY-MM-DD`) | yes | Inclusive; must be on or after `start_date` |
| `level` | integer | yes | **`0`** or **`10`** only |
| `frequency_seconds` | integer or `null` | no | **`0`** or **`null`** only |

**Rules enforced by the API**

- Date range: **`end_date - start_date`** must be **at most 31 days**.
- If your API key is **blocked** (including rate limit or storage breach), the request may be rejected with `error: 1` and a `reason` string.
- **Rate limit:** more than **20** submitted requests in a rolling **1 minute** window may trigger a temporary block (typically **10 minutes**) and rejection.

**Successful `data` payload**

Includes a **`request_id`** field (same as database `id`) plus the fields listed under **Request record**.

---

### List requests

**`GET {BASE_URL}/request/list`**

Returns all requests for your user where the output has **not** been marked deleted (`request_file_deleted` is false or unset). Newest first.

**Success:** HTTP **200**, `error: 0`, `data` is an **array** of request records.

---

### Cancel a request

**`POST {BASE_URL}/request/cancel/{request_id}`**

Schedules cancellation for a request that is **`waiting`** or **`running`**. Status becomes **`cancelling`** while the **lobster-app** worker removes that job’s output files and updates the same database row to **`deleted`** (no separate callback HTTP call).

| Path parameter | Type | Description |
|----------------|------|-------------|
| `request_id` | integer | Request id |

**Success:** HTTP **200**, `error: 0`, `data` is the updated request record.

**Idempotency:** If the request is already **`cancelling`**, the same success envelope is returned.

**Business failure:** HTTP **200**, `error: 1`, `data.reason` explains why cancellation is not allowed (for example wrong `status`).

**HTTP errors**

| Code | When |
|------|------|
| 403 | Not your request |
| 404 | Unknown `request_id` |

---

### Download result zip

**`GET {BASE_URL}/request/download/{request_id}`**

Streams the completed **ZIP** file for a **finished** request (one archive per trading day inside the zip). The server sets download flags on success.

| Path parameter | Type | Description |
|----------------|------|-------------|
| `request_id` | integer | Request id |

**Success:** HTTP **200**, body is raw file bytes; `Content-Type: application/zip`; `Content-Disposition` includes the filename.

**HTTP errors**

| Code | When |
|------|------|
| 403 | Not your request |
| 404 | Unknown id, or file missing on server |
| 409 | Status is not **`finished`** (includes **`cancelling`**, **`waiting`**, **`running`**, etc.) |
| 410 | Files already deleted |

---

### Delete output file

**`DELETE {BASE_URL}/request/{request_id}`**

Deletes the ZIP file on the server for a **finished** request and marks the row **`deleted`** (audit row retained). May unblock your API key if it was blocked for **storage breached** and you are again under the cumulative size limit.

**Success:** HTTP **200**, `error: 0`, `data` includes `id`, `symbol`, `start_date`, `end_date`, `deleted_time`.

**Business failure:** HTTP **200**, `error: 1`, `data.reason` (already deleted, not finished, disk error, etc.).

**HTTP errors**

| Code | When |
|------|------|
| 403 | Not your request |
| 404 | Unknown `request_id` |

---

### API key block state

**`GET {BASE_URL}/request/block-state`**

Returns whether your API key is currently blocked (for example rate limit, storage limit, or manual block).

**Success:** HTTP **200**, `error: 0`, `data`:

| Field | Type | Description |
|-------|------|-------------|
| `blocked` | boolean | Whether the key is blocked |
| `block_reason` | string or null | Human-readable reason |
| `unblock_time` | datetime or null | When the block lifts, if applicable |

**Failure envelope:** HTTP **200**, `error: 1`, `data.reason` (for example no API key row for your user).

**HTTP errors**

| Code | When |
|------|------|
| 403 | Token is not from API-key validation |

---

## Request record (`data` shape)

Fields commonly returned for a single request (JSON types):

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Request id |
| `request_id` | integer | Present on **`POST /request/add`** success; same as `id` |
| `symbol` | string | Ticker |
| `start_date` | date | ISO date string |
| `end_date` | date | ISO date string |
| `level` | integer | `0` or `10` |
| `frequency_seconds` | integer or null | |
| `status` | string | See **Request lifecycle** |
| `requestor_id` | integer or null | Your user id when applicable |
| `request_time` | datetime | When the request was submitted |
| `request_ip` | string or null | Client IP if recorded |
| `task_start_time` | datetime or null | When processing started |
| `task_end_time` | datetime or null | When processing ended |
| `request_file` | string or null | Server path to the ZIP when finished |
| `request_data_size` | integer or null | Approximate payload size metadata |
| `request_downloaded` | boolean | Whether you downloaded via **`GET .../download/...`** |
| `request_downloaded_time` | datetime or null | |
| `request_file_deleted` | boolean or null | Whether output was removed |
| `request_file_deleted_time` | datetime or null | |

Exact nullability may vary by endpoint and row state.

---

## Rejection payload (`POST /request/add`, `error: 1`)

When a new request is rejected but the HTTP status is **200**, `data` echoes your submission fields plus:

| Field | Type |
|-------|------|
| `symbol`, `start_date`, `end_date`, `level`, `frequency_seconds` | same as request |
| `request_ip` | string or null |
| `reason` | string explaining rejection |

---

## Summary table

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/request/add` | Create request |
| `GET` | `/request/list` | List non-deleted requests |
| `POST` | `/request/cancel/{request_id}` | Cancel queued or running request |
| `GET` | `/request/download/{request_id}` | Download ZIP |
| `DELETE` | `/request/{request_id}` | Delete ZIP and mark deleted |
| `GET` | `/request/block-state` | API key block status |

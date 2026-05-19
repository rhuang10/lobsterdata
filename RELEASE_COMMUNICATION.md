# LOBSTER Python Package - Release Communication

**Subject: Introducing v0.1.4 – Request Cancellation Support & Enhanced CLI**

---

Dear LOBSTER Community,

Thank you for your valuable feedback! We are excited to announce the release of **v0.1.4** of the LOBSTER Python package. This release introduces important new capabilities, improvements to enhance your data workflow, and critical bug fixes.

## What's New

### 1. **Request Cancellation API Support** ✨

We've added comprehensive support for cancelling in-flight data requests through the new `cancel_request()` method:

```python
from lobsterdata import LobsterClient

client = LobsterClient(api_key="your_key", api_secret="your_secret")

# Cancel a request that is waiting or running
response = client.cancel_request(request_id=12345)
print(f"Request cancelled: {response}")
```

**Key Features:**
- Cancel requests with status `waiting` or `running`
- Automatic status transition to `cancelling` while the backend removes output files
- Full compatibility with the LOBSTER Request API `/request/cancel/{request_id}` endpoint
- Idempotent operation – safe to call multiple times

**When to use:**
- Stop data processing jobs that are no longer needed
- Free up API quota and storage resources
- Manage long-running requests efficiently

### 2. **Enhanced Interactive CLI** 🖥️

The `examples/cli.py` interactive tool now includes a complete `cancel` command alongside existing functionality:

**Available commands:**
- `submit` – Create new data requests interactively
- `ls` – List all active requests with status
- `download` – Download finished request data
- **`cancel` – Cancel waiting or running requests** *(NEW)*
- `delete` – Remove completed request files
- `help` – Show command reference
- `quit` – Exit the CLI

**Try the new cancellation feature:**
```bash
uv run python examples/cli.py
# Then type: cancel
```

The CLI provides an intuitive, menu-driven interface to manage your requests without writing code.

### 3. **Critical Bug Fixes** 🐛

This release addresses two important stability issues reported by the community:

**Deadlock Resolution**
- Fixed a deadlock bug that occurred when multiple concurrent tasks attempted to construct the same data simultaneously
- Improves reliability in multi-threaded and distributed processing scenarios

**ITCH Data Corruption Handling**
- Fixed a crash bug that occurred when processing corrupted binary ITCH data files
- Now gracefully handles malformed data with proper error reporting

### 4. **Python Package Version** 📦

**Release:** `lobsterdata==0.1.4`

Install or upgrade:
```bash
uv add lobsterdata
# or
pip install --upgrade lobsterdata
```

## API Endpoint Reference

The new `cancel_request()` method corresponds to the LOBSTER Request API endpoint:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/request/cancel/{request_id}` | Cancel queued or running request |

**Response Format:**
- HTTP 200 with status updated to `cancelling`
- Full request record returned
- Idempotent – already-cancelling requests return the same success envelope

**Error Handling:**
- HTTP 403: Not your request
- HTTP 404: Unknown request ID
- `error: 1` with `data.reason`: Business-level failure (wrong status, already deleted, etc.)

## Migration Notes

This is a **backward-compatible** release. Existing code using `submit_request()`, `download_request()`, `delete_request()`, and other methods continues to work unchanged.

**If you were previously working around the missing cancellation functionality**, you can now:
1. Replace manual workarounds with `client.cancel_request()`
2. Simplify request lifecycle management in your workflows
3. Use the CLI's `cancel` command for one-off operations

## Documentation

Complete API documentation is available in:
- **Request lifecycle states:** See `dev-docs/request-api.md` for full endpoint reference
- **Python client examples:** Check `examples/cli.py` for cancellation usage patterns
- **Inline docstrings:** All methods include detailed parameter and return value documentation

## Getting Started

### For New Users
```bash
# Install the package
uv add lobsterdata

# Copy and configure credentials
cp .env.example .env
# Edit .env with your API key and secret

# Try the interactive CLI
uv run python examples/cli.py
```

### For Existing Users
```bash
# Upgrade to the latest version
uv sync
# or manually: pip install --upgrade lobsterdata

# Check your code uses the correct import
from lobsterdata import LobsterClient
```

## Questions & Support

If you have questions about the new cancellation functionality or any other features, please reach out to our support team or open an issue on our repository.

---

**Release Date:** May 19, 2026  
**Version:** 0.1.4  
**Requirements:** Python 3.13+

Happy data processing!

**The LOBSTER Team**

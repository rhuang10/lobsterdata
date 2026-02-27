"""
Unit tests for LobsterClient.

All HTTP calls are mocked via pytest-mock / unittest.mock so no real
network connection or credentials are needed.
"""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from lobsterdata.client import LobsterClient

# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------

FAKE_TOKEN = "fake-access-token-abc123"
PILOT_BASE = "https://dev.lobsterdata.com/api"
PROD_BASE = "https://lobsterdata.com/api"


def _mock_auth_response(token: str = FAKE_TOKEN) -> MagicMock:
    """Return a mock response for the /api-key/validate endpoint."""
    resp = MagicMock()
    resp.json.return_value = {"access_token": token, "expires_in": 86400, "user_id": 1}
    resp.raise_for_status.return_value = None
    return resp


def _make_client(is_pilot: bool = True) -> LobsterClient:
    """Construct a LobsterClient with the auth call mocked out."""
    with patch("lobsterdata.client.requests.post", return_value=_mock_auth_response()):
        return LobsterClient(
            api_key="test-key", api_secret="test-secret", is_pilot=is_pilot
        )


def _mock_get(json_data: dict) -> MagicMock:
    """Return a mock GET response with the given JSON payload."""
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# Construction / authentication
# ---------------------------------------------------------------------------


class TestInit:
    def test_pilot_base_url(self):
        client = _make_client(is_pilot=True)
        assert client.base_url == PILOT_BASE

    def test_prod_base_url(self):
        client = _make_client(is_pilot=False)
        assert client.base_url == PROD_BASE

    def test_access_token_stored(self):
        client = _make_client()
        assert client.access_token == FAKE_TOKEN

    def test_auth_called_with_correct_params(self):
        with patch(
            "lobsterdata.client.requests.post", return_value=_mock_auth_response()
        ) as mock_post:
            LobsterClient(api_key="k", api_secret="s", is_pilot=True)
            mock_post.assert_called_once_with(
                f"{PILOT_BASE}/api-key/validate",
                params={"api_key": "k", "api_secret": "s"},
            )

    def test_auth_http_error_raises(self):
        import requests as req_lib

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req_lib.HTTPError("401 Unauthorized")
        with patch("lobsterdata.client.requests.post", return_value=mock_resp):
            with pytest.raises(req_lib.HTTPError):
                LobsterClient(api_key="bad", api_secret="bad", is_pilot=True)


# ---------------------------------------------------------------------------
# Auth headers property
# ---------------------------------------------------------------------------


class TestAuthHeaders:
    def test_bearer_token_in_headers(self):
        client = _make_client()
        assert client._auth_headers == {"Authorization": f"Bearer {FAKE_TOKEN}"}


# ---------------------------------------------------------------------------
# list_requests
# ---------------------------------------------------------------------------

SAMPLE_REQUESTS = [
    {
        "id": 1,
        "request_id": 1,
        "symbol": "AAPL",
        "start_date": "2025-02-03",
        "end_date": "2025-02-07",
        "level": 10,
        "status": "finished",
        "request_data_size": 1024 * 1024 * 5,
        "request_file_deleted": False,
    },
    {
        "id": 2,
        "request_id": 2,
        "symbol": "GOOG",
        "start_date": "2025-02-03",
        "end_date": "2025-02-07",
        "level": 10,
        "status": "waiting",
        "request_data_size": 0,
        "request_file_deleted": False,
    },
    {
        "id": 3,
        "request_id": 3,
        "symbol": "AMZN",
        "start_date": "2025-02-03",
        "end_date": "2025-02-07",
        "level": 10,
        "status": "running",
        "request_data_size": 0,
        "request_file_deleted": False,
    },
    {
        "id": 4,
        "request_id": 4,
        "symbol": "NVDA",
        "start_date": "2025-02-03",
        "end_date": "2025-02-07",
        "level": 10,
        "status": "finished",
        "request_data_size": 1024 * 1024 * 10,
        "request_file_deleted": True,  # already deleted
    },
]


class TestListRequests:
    def test_returns_data_list(self):
        client = _make_client()
        with patch(
            "lobsterdata.client.requests.get",
            return_value=_mock_get({"data": SAMPLE_REQUESTS}),
        ):
            result = client.list_requests()
        assert len(result) == 4
        assert result[0]["symbol"] == "AAPL"

    def test_empty_data_key(self):
        client = _make_client()
        with patch(
            "lobsterdata.client.requests.get",
            return_value=_mock_get({"data": []}),
        ):
            result = client.list_requests()
        assert result == []

    def test_calls_correct_url(self):
        client = _make_client()
        with patch(
            "lobsterdata.client.requests.get",
            return_value=_mock_get({"data": []}),
        ) as mock_get:
            client.list_requests()
            mock_get.assert_called_once_with(
                f"{PILOT_BASE}/request/list",
                headers=client._auth_headers,
            )


# ---------------------------------------------------------------------------
# get_request
# ---------------------------------------------------------------------------


class TestGetRequest:
    def test_finds_by_request_id(self):
        client = _make_client()
        with patch(
            "lobsterdata.client.requests.get",
            return_value=_mock_get({"data": SAMPLE_REQUESTS}),
        ):
            req = client.get_request(1)
        assert req is not None
        assert req["symbol"] == "AAPL"

    def test_returns_none_when_not_found(self):
        client = _make_client()
        with patch(
            "lobsterdata.client.requests.get",
            return_value=_mock_get({"data": SAMPLE_REQUESTS}),
        ):
            req = client.get_request(999)
        assert req is None

    def test_accepts_string_id(self):
        client = _make_client()
        with patch(
            "lobsterdata.client.requests.get",
            return_value=_mock_get({"data": SAMPLE_REQUESTS}),
        ):
            req = client.get_request("2")
        assert req is not None
        assert req["symbol"] == "GOOG"


# ---------------------------------------------------------------------------
# list_alive_requests
# ---------------------------------------------------------------------------


class TestListAliveRequests:
    def test_returns_waiting_running_and_undeleted_finished(self):
        client = _make_client()
        with patch(
            "lobsterdata.client.requests.get",
            return_value=_mock_get({"data": SAMPLE_REQUESTS}),
        ):
            alive = client.list_alive_requests()
        statuses = {r["status"] for r in alive}
        # finished+deleted (id=4) should be excluded
        ids = {r["id"] for r in alive}
        assert 4 not in ids
        assert statuses <= {"waiting", "running", "finished"}

    def test_excludes_deleted_finished(self):
        client = _make_client()
        with patch(
            "lobsterdata.client.requests.get",
            return_value=_mock_get({"data": SAMPLE_REQUESTS}),
        ):
            alive = client.list_alive_requests()
        for r in alive:
            assert not (r["status"] == "finished" and r["request_file_deleted"])


# ---------------------------------------------------------------------------
# list_downloadable_requests
# ---------------------------------------------------------------------------


class TestListDownloadableRequests:
    def test_only_nonzero_undeleted(self):
        client = _make_client()
        with patch(
            "lobsterdata.client.requests.get",
            return_value=_mock_get({"data": SAMPLE_REQUESTS}),
        ):
            downloadable = client.list_downloadable_requests()
        # Only id=1 qualifies (finished, data_size > 0, not deleted)
        assert len(downloadable) == 1
        assert downloadable[0]["id"] == 1


# ---------------------------------------------------------------------------
# submit_request
# ---------------------------------------------------------------------------


class TestSubmitRequest:
    def test_returns_parsed_json(self):
        client = _make_client()
        fake_response = {"data": {"request_id": 42}, "error": 0}
        mock_resp = MagicMock()
        mock_resp.json.return_value = fake_response
        mock_resp.raise_for_status.return_value = None

        with patch("lobsterdata.client.requests.post", return_value=mock_resp):
            result = client.submit_request(
                symbol="AAPL",
                start_date="2025-02-03",
                end_date="2025-02-07",
                level=10,
                exchange="NASDAQ",
            )
        assert result["data"]["request_id"] == 42

    def test_calls_correct_url_and_payload(self):
        client = _make_client()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": {"request_id": 1}}
        mock_resp.raise_for_status.return_value = None

        with patch(
            "lobsterdata.client.requests.post", return_value=mock_resp
        ) as mock_post:
            client.submit_request(
                "MSFT", "2025-01-01", "2025-01-05", level=10, exchange="NASDAQ"
            )
            _, kwargs = mock_post.call_args
            assert kwargs["json"]["symbol"] == "MSFT"
            assert kwargs["json"]["level"] == 10


# ---------------------------------------------------------------------------
# download_request
# ---------------------------------------------------------------------------


class TestDownloadRequest:
    def test_saves_file_and_returns_path(self, tmp_path):
        client = _make_client()
        fake_content = b"PK\x03\x04fake zip content"

        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.headers = {
            "Content-Disposition": 'attachment; filename="AAPL_data.zip"'
        }
        mock_resp.iter_content.return_value = [fake_content]

        with patch("lobsterdata.client.requests.get", return_value=mock_resp):
            filepath = client.download_request(42, download_dir=str(tmp_path))

        assert os.path.exists(filepath)
        assert filepath.endswith("AAPL_data.zip")
        with open(filepath, "rb") as f:
            assert f.read() == fake_content

    def test_fallback_filename_when_no_content_disposition(self, tmp_path):
        client = _make_client()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.headers = {}
        mock_resp.iter_content.return_value = [b"data"]

        with patch("lobsterdata.client.requests.get", return_value=mock_resp):
            filepath = client.download_request(99, download_dir=str(tmp_path))

        assert "lobster_request_99" in filepath

    def test_creates_download_dir(self, tmp_path):
        client = _make_client()
        new_dir = tmp_path / "nested" / "dir"
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.headers = {}
        mock_resp.iter_content.return_value = [b"data"]

        with patch("lobsterdata.client.requests.get", return_value=mock_resp):
            client.download_request(1, download_dir=str(new_dir))

        assert new_dir.exists()


# ---------------------------------------------------------------------------
# delete_request
# ---------------------------------------------------------------------------


class TestDeleteRequest:
    def test_calls_delete_endpoint(self):
        client = _make_client()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"error": 0, "message": "deleted"}
        mock_resp.raise_for_status.return_value = None

        with patch(
            "lobsterdata.client.requests.delete", return_value=mock_resp
        ) as mock_del:
            result = client.delete_request(42)
            mock_del.assert_called_once_with(
                f"{PILOT_BASE}/request/42",
                headers=client._auth_headers,
            )
        assert result["error"] == 0

    def test_http_error_propagates(self):
        import requests as req_lib

        client = _make_client()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req_lib.HTTPError("404")

        with patch("lobsterdata.client.requests.delete", return_value=mock_resp):
            with pytest.raises(req_lib.HTTPError):
                client.delete_request(999)


# ---------------------------------------------------------------------------
# download_and_cleanup
# ---------------------------------------------------------------------------


class TestDownloadAndCleanup:
    def test_downloads_and_deletes_all_downloadable(self, tmp_path):
        client = _make_client()
        downloadable = [SAMPLE_REQUESTS[0]]  # only id=1 is downloadable

        mock_get_list = _mock_get({"data": SAMPLE_REQUESTS})
        mock_get_file = MagicMock()
        mock_get_file.raise_for_status.return_value = None
        mock_get_file.headers = {}
        mock_get_file.iter_content.return_value = [b"zip data"]

        mock_del = MagicMock()
        mock_del.json.return_value = {"error": 0}
        mock_del.raise_for_status.return_value = None

        def get_side_effect(url, **kwargs):
            if "download" in url:
                return mock_get_file
            return mock_get_list

        with patch("lobsterdata.client.requests.get", side_effect=get_side_effect):
            with patch("lobsterdata.client.requests.delete", return_value=mock_del):
                saved = client.download_and_cleanup(download_dir=str(tmp_path))

        assert len(saved) == 1

    def test_skips_404_silently(self, tmp_path):
        import requests as req_lib

        client = _make_client()
        mock_get_list = _mock_get({"data": SAMPLE_REQUESTS})

        mock_get_file = MagicMock()
        http_err = req_lib.HTTPError("404")
        http_err.response = MagicMock()
        http_err.response.status_code = 404
        mock_get_file.raise_for_status.side_effect = http_err

        def get_side_effect(url, **kwargs):
            if "download" in url:
                return mock_get_file
            return mock_get_list

        with patch("lobsterdata.client.requests.get", side_effect=get_side_effect):
            saved = client.download_and_cleanup(download_dir=str(tmp_path))

        assert saved == []


# ---------------------------------------------------------------------------
# get_block_state
# ---------------------------------------------------------------------------


class TestGetBlockState:
    def test_returns_unblocked_state(self):
        client = _make_client()
        payload = {"blocked": False, "block_reason": None, "unblock_time": None}
        with patch(
            "lobsterdata.client.requests.get",
            return_value=_mock_get({"error": 0, "data": payload}),
        ):
            state = client.get_block_state()
        assert state["blocked"] is False
        assert state["block_reason"] is None
        assert state["unblock_time"] is None

    def test_returns_blocked_state(self):
        client = _make_client()
        payload = {
            "blocked": True,
            "block_reason": "Too many requests",
            "unblock_time": "2026-02-27T12:30:00",
        }
        with patch(
            "lobsterdata.client.requests.get",
            return_value=_mock_get({"error": 0, "data": payload}),
        ):
            state = client.get_block_state()
        assert state["blocked"] is True
        assert state["block_reason"] == "Too many requests"
        assert state["unblock_time"] == "2026-02-27T12:30:00"

    def test_returns_storage_blocked_state(self):
        client = _make_client()
        payload = {
            "blocked": True,
            "block_reason": "Storage breached",
            "unblock_time": None,
        }
        with patch(
            "lobsterdata.client.requests.get",
            return_value=_mock_get({"error": 0, "data": payload}),
        ):
            state = client.get_block_state()
        assert state["block_reason"] == "Storage breached"

    def test_calls_correct_url(self):
        client = _make_client()
        with patch(
            "lobsterdata.client.requests.get",
            return_value=_mock_get({"error": 0, "data": {}}),
        ) as mock_get:
            client.get_block_state()
            mock_get.assert_called_once_with(
                f"{PILOT_BASE}/request/block-state",
                headers=client._auth_headers,
            )

    def test_http_error_propagates(self):
        import requests as req_lib

        client = _make_client()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req_lib.HTTPError("403")
        with patch("lobsterdata.client.requests.get", return_value=mock_resp):
            with pytest.raises(req_lib.HTTPError):
                client.get_block_state()

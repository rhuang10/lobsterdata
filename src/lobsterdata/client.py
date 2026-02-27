"""
LOBSTER Data API Client
"""

from __future__ import annotations

import os
from typing import Optional

import requests


class LobsterClient:
    """
    Client for the LOBSTER Data API.

    Authenticates on construction and stores the access token for subsequent calls.

    Args:
        api_key:    Your LOBSTER API key.
        api_secret: Your LOBSTER API secret.
        is_pilot:   If True, use the pilot/dev endpoint (dev.lobsterdata.com).
                    If False, use the production endpoint (lobsterdata.com).
    """

    _PILOT_BASE_URL = "https://dev.lobsterdata.com/api"
    _PROD_BASE_URL = "https://lobsterdata.com/api"

    def __init__(self, api_key: str, api_secret: str, is_pilot: bool = False) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = self._PILOT_BASE_URL if is_pilot else self._PROD_BASE_URL

        # Authenticate immediately and store the access token
        self.access_token: str = self._validate_api_key()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}

    def _validate_api_key(self) -> str:
        """
        Exchange API key + secret for a bearer access token.
        The token is valid for 24 hours.

        Returns:
            The access token string.

        Raises:
            requests.HTTPError: If authentication fails.
        """
        url = f"{self.base_url}/api-key/validate"
        params = {"api_key": self.api_key, "api_secret": self.api_secret}

        response = requests.post(url, params=params)
        response.raise_for_status()

        data = response.json()
        return data["access_token"]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit_request(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        level: int = 10,
        exchange: str = "NASDAQ",
    ) -> dict:
        """
        Submit a LOBSTER data construction request.

        Args:
            symbol:     Stock ticker symbol (e.g. "AAPL").
            start_date: Start date in YYYY-MM-DD format.
            end_date:   End date in YYYY-MM-DD format.
            level:      Order book depth level (0 or 10, default: 10).
            exchange:   Exchange name (default: "NASDAQ").

        Returns:
            Parsed JSON response from the API, including ``request_id``.

        Raises:
            requests.HTTPError: If the API returns an error status.
        """
        url = f"{self.base_url}/request/add"
        payload = {
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "level": level,
            "exchange": exchange,
        }

        response = requests.post(
            url,
            headers={**self._auth_headers, "Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def list_requests(self) -> list[dict]:
        """
        List all completed requests for the authenticated user.

        Returns:
            List of request dictionaries.

        Raises:
            requests.HTTPError: If the API returns an error status.
        """
        url = f"{self.base_url}/request/list"
        response = requests.get(url, headers=self._auth_headers)
        response.raise_for_status()
        return response.json().get("data", [])

    def get_request(self, request_id: str | int) -> dict | None:
        """
        Look up a single request by its ID from the completed-request list.

        Args:
            request_id: The ID returned when the request was submitted.

        Returns:
            The request dict if found, or ``None`` if not yet visible in the list.

        Raises:
            requests.HTTPError: If the list endpoint returns an error status.
        """
        all_requests = self.list_requests()
        for req in all_requests:
            if str(req.get("request_id") or req.get("id")) == str(request_id):
                return req
        return None

    def list_alive_requests(self) -> list[dict]:
        """
        Return all requests that are currently queued or being processed
        (status is ``'waiting'`` or ``'running'``).

        Returns:
            Filtered list of request dictionaries that are not yet complete.

        Raises:
            requests.HTTPError: If the list endpoint returns an error status.
        """
        return [
            req
            for req in self.list_requests()
            if (
                req.get("status") in ("waiting", "running", "finished")
                and not req.get("request_file_deleted", False)
            )
        ]

    def list_downloadable_requests(self) -> list[dict]:
        """
        Return all completed requests that have data available for download
        (status ``'finished'``, data size > 0 and file not yet deleted).

        Returns:
            Filtered list of request dictionaries ready to download.

        Raises:
            requests.HTTPError: If the list endpoint returns an error status.
        """
        return [
            req
            for req in self.list_requests()
            if req.get("status") == "finished"
            and req.get("request_data_size", 0) > 0
            and not req.get("request_file_deleted", False)
        ]

    def download_request(
        self, request_id: str | int, download_dir: str = "./downloads"
    ) -> str:
        """
        Download the data file for a completed request.

        Args:
            request_id:   The ID of the request to download.
            download_dir: Local directory in which to save the file (created if absent).

        Returns:
            Absolute path of the saved file.

        Raises:
            requests.HTTPError: If the download fails (e.g. 404 = file not on server).
        """
        os.makedirs(download_dir, exist_ok=True)

        url = f"{self.base_url}/request/download/{request_id}"
        response = requests.get(url, headers=self._auth_headers, stream=True)
        response.raise_for_status()

        # Determine filename from Content-Disposition header, or fall back to a default
        filename: Optional[str] = None
        content_disp = response.headers.get("Content-Disposition", "")
        if "filename=" in content_disp:
            filename = content_disp.split("filename=")[1].strip('"')
        if not filename:
            filename = f"lobster_request_{request_id}.zip"

        filepath = os.path.join(download_dir, filename)
        with open(filepath, "wb") as fh:
            for chunk in response.iter_content(chunk_size=8192):
                fh.write(chunk)

        return os.path.abspath(filepath)

    def delete_request(self, request_id: str | int) -> dict:
        """
        Delete a completed request (and its data file) from the server.

        Args:
            request_id: The ID of the request to delete.

        Returns:
            Parsed JSON response from the API.

        Raises:
            requests.HTTPError: If the API returns an error status.
        """
        url = f"{self.base_url}/request/{request_id}"
        response = requests.delete(url, headers=self._auth_headers)
        response.raise_for_status()
        return response.json()

    def download_and_cleanup(self, download_dir: str = "./downloads") -> list[str]:
        """
        Download every completed request that has data and has not yet been deleted,
        then remove each file from the server after a successful download.

        Args:
            download_dir: Local directory in which to save files.

        Returns:
            List of absolute paths for all successfully downloaded files.
        """
        all_requests = self.list_downloadable_requests()

        downloadable = all_requests

        saved_files: list[str] = []

        for req in downloadable:
            request_id = req.get("id")
            try:
                filepath = self.download_request(request_id, download_dir=download_dir)
                self.delete_request(request_id)
                saved_files.append(filepath)
            except requests.exceptions.HTTPError as exc:
                if exc.response is not None and exc.response.status_code == 404:
                    # File recorded in DB but not present on server – skip silently
                    continue
                raise

        return saved_files

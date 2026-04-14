"""
Unit tests for the example CLI helper functions.

Covers pure, side-effect-free helpers from:
  - examples/cli.py         (_prompt_date, _prompt_level)
  - examples/bulk_request.py (_parse_date, _parse_level, _load_symbols)

All tests are fully offline – no network calls, no real credentials required.
The dummy credentials injected by conftest.py prevent the module-level
sys.exit check from firing on import.
"""

from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path
from unittest.mock import patch

import bulk_request as br
import cli as cli_mod
import pytest

# ---------------------------------------------------------------------------
# cli._prompt_date
# ---------------------------------------------------------------------------


class TestPromptDate:
    """_prompt_date should loop until the user types a valid YYYY-MM-DD date."""

    def test_valid_date_returned(self):
        with patch("builtins.input", return_value="2026-04-01"):
            result = cli_mod._prompt_date("Enter date")
        assert result == date(2026, 4, 1)

    def test_invalid_format_retries(self, capsys):
        with patch("builtins.input", side_effect=["not-a-date", "2026-04-01"]):
            result = cli_mod._prompt_date("Enter date")
        assert result == date(2026, 4, 1)
        assert "Invalid format" in capsys.readouterr().out

    def test_invalid_calendar_date_retries(self, capsys):
        # "2026-13-99" passes the regex but fails date.fromisoformat
        with patch("builtins.input", side_effect=["2026-13-99", "2026-04-01"]):
            result = cli_mod._prompt_date("Enter date")
        assert result == date(2026, 4, 1)
        assert "Invalid date" in capsys.readouterr().out

    def test_empty_input_retries(self, capsys):
        # _prompt has no default for dates, so an empty string must be re-asked
        with patch("builtins.input", side_effect=["", "2026-04-01"]):
            result = cli_mod._prompt_date("Enter date")
        assert result == date(2026, 4, 1)


# ---------------------------------------------------------------------------
# cli._prompt_level
# ---------------------------------------------------------------------------


class TestPromptLevel:
    """_prompt_level should accept 0 or 10, retry on anything else."""

    def test_default_returns_10(self):
        # Empty input → _prompt returns the default "10"
        with patch("builtins.input", return_value=""):
            result = cli_mod._prompt_level()
        assert result == 10

    def test_explicit_10(self):
        with patch("builtins.input", return_value="10"):
            assert cli_mod._prompt_level() == 10

    def test_explicit_0(self):
        with patch("builtins.input", return_value="0"):
            assert cli_mod._prompt_level() == 0

    def test_invalid_number_retries(self, capsys):
        with patch("builtins.input", side_effect=["5", "10"]):
            result = cli_mod._prompt_level()
        assert result == 10
        assert "Invalid level" in capsys.readouterr().out

    def test_non_integer_retries(self, capsys):
        with patch("builtins.input", side_effect=["abc", "10"]):
            result = cli_mod._prompt_level()
        assert result == 10
        assert "must be an integer" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# bulk_request._parse_date  (argparse type converter)
# ---------------------------------------------------------------------------


class TestParseDate:
    def test_valid_date(self):
        assert br._parse_date("2026-04-01") == date(2026, 4, 1)

    def test_wrong_separator_raises(self):
        with pytest.raises(argparse.ArgumentTypeError, match="Expected format"):
            br._parse_date("01-04-2026")

    def test_no_separator_raises(self):
        with pytest.raises(argparse.ArgumentTypeError, match="Expected format"):
            br._parse_date("20260401")

    def test_invalid_calendar_date_raises(self):
        with pytest.raises(argparse.ArgumentTypeError):
            br._parse_date("2026-13-01")


# ---------------------------------------------------------------------------
# bulk_request._parse_level  (argparse type converter)
# ---------------------------------------------------------------------------


class TestParseLevel:
    def test_level_10(self):
        assert br._parse_level("10") == 10

    def test_level_0(self):
        assert br._parse_level("0") == 0

    def test_invalid_number_raises(self):
        with pytest.raises(argparse.ArgumentTypeError, match="Invalid level"):
            br._parse_level("5")

    def test_negative_raises(self):
        with pytest.raises(argparse.ArgumentTypeError, match="Invalid level"):
            br._parse_level("-1")

    def test_non_integer_raises(self):
        with pytest.raises(argparse.ArgumentTypeError, match="integer"):
            br._parse_level("abc")


# ---------------------------------------------------------------------------
# bulk_request._load_symbols  (CSV ticker loader)
# ---------------------------------------------------------------------------


class TestLoadSymbols:
    def _write_csv(
        self, tmp_path: Path, rows: list[dict], fieldnames: list[str]
    ) -> Path:
        p = tmp_path / "tickers.csv"
        with p.open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return p

    def test_basic_load(self, tmp_path):
        p = self._write_csv(
            tmp_path, [{"Ticker": "AAPL"}, {"Ticker": "MSFT"}], ["Ticker"]
        )
        assert br._load_symbols(p) == ["AAPL", "MSFT"]

    def test_deduplication_preserves_order(self, tmp_path):
        rows = [{"Ticker": "AAPL"}, {"Ticker": "MSFT"}, {"Ticker": "AAPL"}]
        p = self._write_csv(tmp_path, rows, ["Ticker"])
        assert br._load_symbols(p) == ["AAPL", "MSFT"]

    def test_lowercase_normalized_to_upper(self, tmp_path):
        p = self._write_csv(tmp_path, [{"Ticker": "aapl"}], ["Ticker"])
        assert br._load_symbols(p) == ["AAPL"]

    def test_skips_empty_and_whitespace_tickers(self, tmp_path):
        rows = [{"Ticker": "AAPL"}, {"Ticker": ""}, {"Ticker": "  "}]
        p = self._write_csv(tmp_path, rows, ["Ticker"])
        assert br._load_symbols(p) == ["AAPL"]

    def test_extra_columns_ignored(self, tmp_path):
        rows = [
            {"Ticker": "AAPL", "Name": "Apple"},
            {"Ticker": "MSFT", "Name": "Microsoft"},
        ]
        p = self._write_csv(tmp_path, rows, ["Ticker", "Name"])
        assert br._load_symbols(p) == ["AAPL", "MSFT"]

    def test_missing_ticker_column_raises(self, tmp_path):
        p = self._write_csv(tmp_path, [{"Symbol": "AAPL"}], ["Symbol"])
        with pytest.raises(ValueError, match="Ticker"):
            br._load_symbols(p)

    def test_empty_csv_returns_empty_list(self, tmp_path):
        p = self._write_csv(tmp_path, [], ["Ticker"])
        assert br._load_symbols(p) == []

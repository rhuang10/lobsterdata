"""
pytest configuration shared across the test suite.

- Adds examples/ to sys.path so test_examples.py can import cli and bulk_request
  as regular modules.
- Sets dummy API credentials in os.environ *before* the example modules are
  imported, so their module-level credential check doesn't call sys.exit during
  test collection.  load_dotenv(override=False) (the default) will not override
  values that are already present in os.environ.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ── sys.path ──────────────────────────────────────────────────────────────────
_EXAMPLES_DIR = str(Path(__file__).parent.parent / "examples")
if _EXAMPLES_DIR not in sys.path:
    sys.path.insert(0, _EXAMPLES_DIR)

# ── dummy credentials ─────────────────────────────────────────────────────────
os.environ.setdefault("LOBSTER_API_KEY", "test-key-pytest")
os.environ.setdefault("LOBSTER_API_SECRET", "test-secret-pytest")

#!/usr/bin/env bash
# =============================================================================
# publish.sh – Build and publish lobsterdata to PyPI
#
# Usage:
#   ./publish.sh            # publish to PyPI (production)
#   ./publish.sh --test     # publish to TestPyPI first (recommended for dry run)
#
# Prerequisites:
#   1. uv dev dependencies installed:  uv sync --group dev
#   2. A PyPI API token set as environment variable:
#        export PYPI_TOKEN="pypi-..."
#      Or for TestPyPI:
#        export TEST_PYPI_TOKEN="pypi-..."
#
#   Alternatively, configure ~/.pypirc (see: https://packaging.python.org/en/latest/specifications/pypirc/)
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
USE_TEST_PYPI=false
for arg in "$@"; do
    case $arg in
        --test) USE_TEST_PYPI=true ;;
        *) echo "Unknown argument: $arg"; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Step 1: Run tests – do not publish a broken package
# ---------------------------------------------------------------------------
echo "==> Running test suite..."
uv run pytest tests/ -q
echo "    Tests passed."

# ---------------------------------------------------------------------------
# Step 2: Clean previous build artefacts
# ---------------------------------------------------------------------------
echo "==> Cleaning dist/ ..."
rm -rf dist/

# ---------------------------------------------------------------------------
# Step 3: Build source distribution and wheel
# ---------------------------------------------------------------------------
echo "==> Building package..."
uv build
echo "    Build artefacts:"
ls -lh dist/

# ---------------------------------------------------------------------------
# Step 4: Check the distribution with twine
# ---------------------------------------------------------------------------
echo "==> Checking distribution with twine..."
uv run twine check dist/*

# ---------------------------------------------------------------------------
# Step 5: Upload to PyPI or TestPyPI
# ---------------------------------------------------------------------------
if [ "$USE_TEST_PYPI" = true ]; then
    echo "==> Uploading to TestPyPI..."
    if [ -n "${TEST_PYPI_TOKEN:-}" ]; then
        uv run twine upload \
            --repository testpypi \
            --username __token__ \
            --password "$TEST_PYPI_TOKEN" \
            dist/*
    else
        # Fall back to ~/.pypirc configuration
        uv run twine upload --repository testpypi dist/*
    fi
    echo ""
    echo "✓ Published to TestPyPI!"
    echo "  Install with:"
    echo "    pip install --index-url https://test.pypi.org/simple/ lobsterdata"
else
    echo "==> Uploading to PyPI..."
    if [ -n "${PYPI_TOKEN:-}" ]; then
        uv run twine upload \
            --username __token__ \
            --password "$PYPI_TOKEN" \
            dist/*
    else
        # Fall back to ~/.pypirc configuration
        uv run twine upload dist/*
    fi
    echo ""
    echo "✓ Published to PyPI!"
    echo "  Install with:"
    echo "    pip install lobsterdata"
fi

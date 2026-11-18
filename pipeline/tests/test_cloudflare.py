"""Runs the Cloudflare Function's Node tests, so `uv run pytest` covers the vote API too."""

import shutil
import subprocess
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parents[2] / "cloudflare" / "test" / "votes.test.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is not installed")
def test_votes_function():
    result = subprocess.run(["node", "--test", str(TESTS)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr

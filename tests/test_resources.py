"""Tests for gui/resources.py — automatic Start-OoProxy.ps1 generation."""

from __future__ import annotations

import pytest
from pathlib import Path
from gui.resources import set_ooproxy_home, get_ooproxy_home, START_OOPROXY_TEMPLATE


def test_set_ooproxy_home_generates_ps1_if_missing(tmp_path: Path):
    """Calling set_ooproxy_home with a valid directory should generate Start-OoProxy.ps1 if missing."""
    # Create valid ooproxy home (needs ooproxy.py)
    ooproxy_py = tmp_path / "ooproxy.py"
    ooproxy_py.touch()

    ps_script = tmp_path / "Start-OoProxy.ps1"
    assert not ps_script.exists()

    # Call set_ooproxy_home
    set_ooproxy_home(tmp_path)

    # Check the active home matches
    assert get_ooproxy_home() == tmp_path

    # Verify Start-OoProxy.ps1 was created and matches the template
    assert ps_script.exists()
    content = ps_script.read_text(encoding="utf-8")
    assert content == START_OOPROXY_TEMPLATE


def test_set_ooproxy_home_does_not_overwrite_existing_ps1(tmp_path: Path):
    """Calling set_ooproxy_home should not overwrite an existing Start-OoProxy.ps1."""
    # Create valid ooproxy home
    ooproxy_py = tmp_path / "ooproxy.py"
    ooproxy_py.touch()

    ps_script = tmp_path / "Start-OoProxy.ps1"
    original_content = "custom content that should not be overwritten"
    ps_script.write_text(original_content, encoding="utf-8")

    # Call set_ooproxy_home
    set_ooproxy_home(tmp_path)

    # Verify Start-OoProxy.ps1 exists and has NOT been overwritten
    assert ps_script.exists()
    content = ps_script.read_text(encoding="utf-8")
    assert content == original_content

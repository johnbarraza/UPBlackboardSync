"""Tests for OS-dependent utility helpers."""

import sys

import pytest

from blackboard_sync.qt.utils import clean_external_env


@pytest.mark.skipif(
    not sys.platform.startswith("linux"),
    reason="LD_LIBRARY_PATH sanitizing only applies on Linux",
)
def test_clean_external_env_drops_pyinstaller_libs(monkeypatch):
    # Simulate a frozen (PyInstaller onedir) process.
    monkeypatch.setenv("LD_LIBRARY_PATH", "/opt/BlackboardSync/_internal")
    monkeypatch.setenv("LD_PRELOAD", "/opt/BlackboardSync/_internal/libfoo.so")
    monkeypatch.delenv("LD_LIBRARY_PATH_ORIG", raising=False)

    env = clean_external_env()

    # xdg-open must NOT inherit the bundled lib paths.
    assert "_internal" not in env.get("LD_LIBRARY_PATH", "")
    assert "LD_LIBRARY_PATH" not in env
    assert "LD_PRELOAD" not in env


@pytest.mark.skipif(
    not sys.platform.startswith("linux"),
    reason="LD_LIBRARY_PATH sanitizing only applies on Linux",
)
def test_clean_external_env_restores_original(monkeypatch):
    # PyInstaller saves the user's original path in LD_LIBRARY_PATH_ORIG.
    monkeypatch.setenv("LD_LIBRARY_PATH", "/opt/BlackboardSync/_internal")
    monkeypatch.setenv("LD_LIBRARY_PATH_ORIG", "/usr/lib/custom")

    env = clean_external_env()

    assert env["LD_LIBRARY_PATH"] == "/usr/lib/custom"

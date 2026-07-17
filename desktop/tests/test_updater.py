"""Tests for `app.updater.check_for_update` (U-2).

Pure-logic tests — no real network, no qtbot. `requests.get` is monkeypatched
directly on the `updater` module so the module's own reference is patched
(the module does `import requests`, so `updater.requests.get` is the right
patch target).
"""

from __future__ import annotations

import pytest

from app import updater


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:  # no-op success path
        return None

    def json(self) -> dict:
        return self._payload


def _patch_get(monkeypatch, payload: dict) -> None:
    monkeypatch.setattr(
        updater.requests, "get", lambda *args, **kwargs: _FakeResponse(payload)
    )


def test_newer_release_returns_dict(monkeypatch):
    _patch_get(
        monkeypatch,
        {
            "tag_name": "v1.6.0",
            "draft": False,
            "prerelease": False,
            "html_url": "https://github.com/JonasaAugusto/IAprovale/releases/tag/v1.6.0",
        },
    )
    monkeypatch.setattr(updater, "__version__", "1.5.0")

    result = updater.check_for_update()

    assert result == {
        "version": "1.6.0",
        "url": "https://github.com/JonasaAugusto/IAprovale/releases/tag/v1.6.0",
    }


def test_equal_version_returns_none(monkeypatch):
    _patch_get(
        monkeypatch,
        {"tag_name": "v1.5.0", "draft": False, "prerelease": False, "html_url": "x"},
    )
    monkeypatch.setattr(updater, "__version__", "1.5.0")

    assert updater.check_for_update() is None


def test_older_version_returns_none(monkeypatch):
    _patch_get(
        monkeypatch,
        {"tag_name": "v1.4.0", "draft": False, "prerelease": False, "html_url": "x"},
    )
    monkeypatch.setattr(updater, "__version__", "1.5.0")

    assert updater.check_for_update() is None


def test_draft_returns_none(monkeypatch):
    _patch_get(
        monkeypatch,
        {"tag_name": "v1.6.0", "draft": True, "prerelease": False, "html_url": "x"},
    )
    monkeypatch.setattr(updater, "__version__", "1.5.0")

    assert updater.check_for_update() is None


def test_prerelease_returns_none(monkeypatch):
    _patch_get(
        monkeypatch,
        {"tag_name": "v1.6.0", "draft": False, "prerelease": True, "html_url": "x"},
    )
    monkeypatch.setattr(updater, "__version__", "1.5.0")

    assert updater.check_for_update() is None


def test_requests_get_raises_returns_none(monkeypatch):
    def _raise(*args, **kwargs):
        raise ConnectionError("boom")

    monkeypatch.setattr(updater.requests, "get", _raise)
    monkeypatch.setattr(updater, "__version__", "1.5.0")

    assert updater.check_for_update() is None


def test_missing_tag_name_returns_none(monkeypatch):
    _patch_get(monkeypatch, {"draft": False, "prerelease": False, "html_url": "x"})
    monkeypatch.setattr(updater, "__version__", "1.5.0")

    assert updater.check_for_update() is None


def test_malformed_tag_returns_none(monkeypatch):
    _patch_get(
        monkeypatch,
        {"tag_name": "banana", "draft": False, "prerelease": False, "html_url": "x"},
    )
    monkeypatch.setattr(updater, "__version__", "1.5.0")

    assert updater.check_for_update() is None


def test_semver_numeric_ordering(monkeypatch):
    _patch_get(
        monkeypatch,
        {"tag_name": "1.10.0", "draft": False, "prerelease": False, "html_url": "x"},
    )
    monkeypatch.setattr(updater, "__version__", "1.9.0")

    result = updater.check_for_update()

    assert result is not None
    assert result["version"] == "1.10.0"

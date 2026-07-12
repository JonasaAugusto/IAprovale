"""Tests for auth_store: local session persistence (D-01).

Monkeypatches auth_store's APP_DIR/SESSION_FILE module attributes to a
tmp_path so the real %APPDATA% is never touched.
"""

from app import auth_store
from app.auth_store import Session


def _patch_session_file(monkeypatch, tmp_path):
    app_dir = tmp_path / "ConcursoFinder"
    session_file = app_dir / "session.json"
    monkeypatch.setattr(auth_store, "APP_DIR", app_dir)
    monkeypatch.setattr(auth_store, "SESSION_FILE", session_file)
    return session_file


def test_session_roundtrip(monkeypatch, tmp_path):
    _patch_session_file(monkeypatch, tmp_path)

    session = Session(token="tok-1", user_id="uid-1", username="jonas", is_admin=True)
    auth_store.save_session(session)

    loaded = auth_store.load_session()

    assert loaded == session


def test_load_missing_returns_none(monkeypatch, tmp_path):
    _patch_session_file(monkeypatch, tmp_path)

    assert auth_store.load_session() is None


def test_load_corrupt_returns_none(monkeypatch, tmp_path):
    session_file = _patch_session_file(monkeypatch, tmp_path)
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.write_text("{ not json", encoding="utf-8")

    assert auth_store.load_session() is None


def test_clear_removes_file(monkeypatch, tmp_path):
    session_file = _patch_session_file(monkeypatch, tmp_path)

    session = Session(token="tok-1", user_id="uid-1", username="jonas", is_admin=False)
    auth_store.save_session(session)
    assert session_file.exists()

    auth_store.clear_session()

    assert auth_store.load_session() is None
    assert not session_file.exists()

    # clearing an already-absent file must not raise
    auth_store.clear_session()

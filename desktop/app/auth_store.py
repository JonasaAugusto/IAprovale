"""Local session persistence (D-01).

Stores the logged-in user's session as plaintext JSON at %APPDATA%\\ConcursoFinder\\session.json.
This is the documented, accepted trust boundary for this invite-only app
(T-03-SESSION): the token is opaque and per-Windows-user %APPDATA% scoping
is sufficient — no keyring/encryption is used.

A corrupted or missing session file must never crash startup (T-03-CORRUPT):
load_session() returns None on any read/parse failure so the app falls
back to the login screen instead of raising.
"""

import json
from dataclasses import dataclass, asdict

from app.config import APP_DIR, SESSION_FILE


@dataclass(frozen=True)
class Session:
    token: str
    user_id: str
    username: str
    is_admin: bool


def save_session(session: Session) -> None:
    """Atomically write `session` to SESSION_FILE (write to .tmp, then replace)."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    tmp = SESSION_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(session)), encoding="utf-8")
    tmp.replace(SESSION_FILE)  # atomic on Windows (same volume)


def load_session() -> Session | None:
    """Return the persisted Session, or None if missing/corrupt/unreadable."""
    if not SESSION_FILE.exists():
        return None
    try:
        data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        return Session(
            token=data["token"],
            user_id=data["user_id"],
            username=data["username"],
            is_admin=data["is_admin"],
        )
    except (json.JSONDecodeError, OSError, KeyError, TypeError):
        return None


def clear_session() -> None:
    """Remove the session file, if present. Never raises if already absent."""
    SESSION_FILE.unlink(missing_ok=True)

"""Auto-update Nível 1: check GitHub for a newer release, never self-replace
the running binary (U-2). `check_for_update()` is designed to be called from
a background thread (see `app.async_helpers.run_in_background`) and to NEVER
raise — any failure (network, timeout, malformed JSON, invalid version tag,
GitHub rate-limiting) is swallowed and reported as "no update available".

Static imports (`requests`, `packaging.version`) so PyInstaller's static
analysis collects both into the frozen `.exe` — a lazy/deferred import
inside the function body risks being missed by the freezer.
"""

from __future__ import annotations

import requests
from packaging.version import InvalidVersion, Version

from app.version import __version__

_LATEST_RELEASE_URL = (
    "https://api.github.com/repos/JonasaAugusto/IAprovale/releases/latest"
)


def check_for_update() -> dict | None:
    """Return `{"version": str, "url": str}` if GitHub's latest release is
    strictly newer (SemVer) than `__version__`, else `None`.

    Never raises to the caller — any exception along the way (network,
    timeout, non-200 status, malformed JSON, invalid version string) is
    treated as "no update available".
    """
    try:
        resp = requests.get(
            _LATEST_RELEASE_URL,
            timeout=10,
            headers={"Accept": "application/vnd.github+json"},
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("draft") or data.get("prerelease"):
            return None

        tag_name = data.get("tag_name")
        if not tag_name:
            return None

        tag = tag_name.lstrip("vV")
        latest = Version(tag)
        current = Version(__version__)

        if latest > current:
            return {"version": tag, "url": data.get("html_url")}
        return None
    except (requests.RequestException, InvalidVersion, ValueError, KeyError):
        return None
    except Exception:  # noqa: BLE001 - deliberately broad, never raise to caller
        return None

"""Central configuration for the Concurso Finder desktop client.

This is the ONLY module in `desktop/app` allowed to call `os.getenv`.
Every other module must import the constants defined here instead of
reading environment variables directly.

BACKEND_URL defaults to a local uvicorn instance (`http://127.0.0.1:8000`)
so manual/automated testing works out of the box against a locally-run
backend. Set the `CONCURSO_FINDER_BACKEND_URL` environment variable to
point the packaged `.exe` at the real deployed Render backend.
"""

import os
from pathlib import Path

BACKEND_URL = os.getenv("CONCURSO_FINDER_BACKEND_URL", "http://127.0.0.1:8000")
APP_DIR = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming")) / "ConcursoFinder"
SESSION_FILE = APP_DIR / "session.json"
THEME_FILE = APP_DIR / "theme.json"

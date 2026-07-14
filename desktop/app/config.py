"""Central configuration for the Concurso Finder desktop client.

This is the ONLY module in `desktop/app` allowed to call `os.getenv`.
Every other module must import the constants defined here instead of
reading environment variables directly.

BACKEND_URL defaults to the real deployed Render backend so the packaged
`.exe` works out of the box for anyone downloading it, no configuration
needed. Set the `CONCURSO_FINDER_BACKEND_URL` environment variable to
point at a local uvicorn instance instead during development (see
`desktop/run-source-local.bat` / `desktop/dist/ConcursoFinder/run-local.bat`).
"""

import os
from pathlib import Path

BACKEND_URL = os.getenv("CONCURSO_FINDER_BACKEND_URL", "https://iaprovalebackend.onrender.com")
APP_DIR = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming")) / "ConcursoFinder"
SESSION_FILE = APP_DIR / "session.json"
THEME_FILE = APP_DIR / "theme.json"

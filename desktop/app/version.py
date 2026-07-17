"""Single source of truth for the desktop app's version (U-1).

Bump `__version__` here — and ONLY here — on every release. Consumed by
`app/main.py` (shown discreetly in the root window title) and by
`app/updater.py` (compared against GitHub's latest release tag to decide
whether to surface an update notice).
"""

from __future__ import annotations

__version__ = "1.5.0"

"""Post-login screen: `ttk.Notebook` with Busca always + Admin conditionally (D-05/D-06).

`visible_tab_labels(session)` is a pure, Tk-free helper isolating the
tab-visibility decision (["Busca"] + ["Admin"] iff `session.is_admin`) so it
can be unit-tested without a real Tk root.

`build_main_frame(root, session, on_logout, on_toggle_theme, is_dark)`
builds the container: a header row with a "Sair" button (wired to the
injected `on_logout` callback, per 03-UI-SPEC.md's Copywriting Contract —
no confirmation dialog, low-risk) plus a light/dark theme toggle button
(wired to `on_toggle_theme`, labeled for the action it performs), then a
`ttk.Notebook` with `BuscaTab` added unconditionally and `AdminTab` added
only inside an `if session.is_admin` branch — never toggled at runtime via
`.hide()`/`.add()`, since `is_admin` is immutable within a session
(03-RESEARCH.md Pattern 2 / Anti-Patterns).

Admin-tab visibility here is UX only (T-03-ADMIN) — the backend's
`require_admin` dependency remains the actual authorization boundary;
`AdminTab` (Plan 05) already handles a stray `403` gracefully.
"""

from __future__ import annotations

from tkinter import ttk

from app.ui.admin_tab import AdminTab
from app.ui.busca_tab import BuscaTab


def visible_tab_labels(session) -> list[str]:
    """Return the tab labels that should be visible for `session`.

    Pure function, no Tk root required — isolates the tab-visibility
    decision for a Tk-free unit test.
    """
    labels = ["Busca"]
    if session.is_admin:
        labels.append("Admin")
    return labels


def build_main_frame(root, session, on_logout, on_toggle_theme, is_dark) -> ttk.Frame:
    """Build and return the post-login container frame.

    Header row: a "Sair" button wired to `on_logout`, plus a light/dark
    theme toggle button wired to `on_toggle_theme` (labeled "Tema escuro"
    when currently light, "Tema claro" when currently dark). Below it: a
    `ttk.Notebook` with `BuscaTab` (text "Busca") always added, and
    `AdminTab` (text "Admin") added only if `session.is_admin`.
    """
    container = ttk.Frame(root, style="Root.TFrame")

    header = ttk.Frame(container, style="Root.TFrame")
    header.pack(fill="x")

    ttk.Button(
        header,
        text="Sair",
        command=on_logout,
    ).pack(side="right", padx=8, pady=8)

    theme_toggle_label = "Tema claro" if is_dark else "Tema escuro"
    ttk.Button(
        header,
        text=theme_toggle_label,
        command=on_toggle_theme,
    ).pack(side="right", padx=8, pady=8)

    notebook = ttk.Notebook(container)

    busca = BuscaTab(notebook, session)
    notebook.add(busca, text="Busca")

    if session.is_admin:
        admin = AdminTab(notebook, session)
        notebook.add(admin, text="Admin")

    notebook.pack(fill="both", expand=True)

    return container

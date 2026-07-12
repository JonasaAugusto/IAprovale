"""Pre-login screen (first screen shown, per D-06/RESEARCH.md Pattern 2).

`LoginFrame` collects username/password, submits `api_client.login()`
off the main thread via `async_helpers.run_in_background` (Pitfall 1 — a
direct call inside a `command=`/`lambda:` handler would freeze the UI for
the full round-trip, up to Render's ~30-90s cold-start latency), and
reports a constructed `auth_store.Session` upward through `on_success` on
a successful login.

Error handling follows 03-UI-SPEC.md's Error Display Contract: failures
are shown in an inline `Banner.TLabel` directly above the "Entrar" button
(never a modal dialog), displaying the backend's `exc.detail` string
verbatim (Pitfall 4) — never a generic/rephrased message.

This frame does NOT persist the session itself — `auth_store.save_session`
is the entry point's (Plan 06) responsibility, not this reusable screen's.
"""

from __future__ import annotations

from tkinter import ttk

from app import api_client, auth_store
from app.async_helpers import run_in_background
from app.ui import styles


class LoginFrame(ttk.Frame):
    def __init__(self, parent, on_success):
        super().__init__(parent, style="Root.TFrame")
        self._on_success = on_success

        card = ttk.Frame(self, style="Card.TFrame", padding=32)
        card.pack(expand=True)

        ttk.Label(
            card,
            text="Concurso Finder",
            font=styles.FONT_DISPLAY,
            background=styles.COLOR_SECONDARY,
        ).pack(pady=(0, 24))

        ttk.Label(card, text="Usuário", background=styles.COLOR_SECONDARY).pack(
            anchor="w"
        )
        self._username_entry = ttk.Entry(card, width=32)
        self._username_entry.pack(pady=(0, 16))

        ttk.Label(card, text="Senha", background=styles.COLOR_SECONDARY).pack(
            anchor="w"
        )
        self._password_entry = ttk.Entry(card, show="•", width=32)
        self._password_entry.pack(pady=(0, 16))
        self._password_entry.bind("<Return>", self._on_submit)

        self._banner = ttk.Label(card, text="", style="Banner.TLabel", wraplength=400)
        # Hidden until an error occurs (Error Display Contract placement:
        # directly above the primary action button).

        self._entrar_button = ttk.Button(
            card,
            text="Entrar",
            style="Accent.TButton",
            command=self._on_submit,
        )
        self._entrar_button.pack(pady=(8, 0))

    def _on_submit(self, _event=None) -> None:
        username = self._username_entry.get()
        password = self._password_entry.get()

        self._clear_banner()
        self._entrar_button.config(state="disabled")

        run_in_background(
            self.winfo_toplevel(),
            lambda: api_client.login(username, password),
            on_success=self._on_login_success,
            on_error=self._on_login_error,
        )

    def _on_login_success(self, response: dict) -> None:
        self._entrar_button.config(state="normal")
        session = auth_store.Session(
            token=response["token"],
            user_id=response["user_id"],
            username=response["username"],
            is_admin=response["is_admin"],
        )
        self._on_success(session)

    def _on_login_error(self, exc: Exception) -> None:
        self._entrar_button.config(state="normal")
        detail = getattr(exc, "detail", str(exc))
        self._show_banner(detail)

    def _show_banner(self, text: str) -> None:
        self._banner.config(text=text)
        self._banner.pack(fill="x", pady=(0, 8), before=self._entrar_button)

    def _clear_banner(self) -> None:
        self._banner.config(text="")
        self._banner.pack_forget()

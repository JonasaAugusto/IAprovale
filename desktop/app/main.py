"""Entry point: Tk root bootstrap, startup auto-login, frame swap, logout (DESKTOP-01/D-01/D-06).

Wires every module built in Plans 01-06 into a runnable app:

- Creates the single `tk.Tk()` root (D-06 — one window, content swapped
  internally, never multiple `Toplevel`s), sets title/geometry/minsize from
  `styles`' constants, loads the persisted theme preference, and calls
  `styles.apply_theme(root, theme)` exactly once at startup, before any
  frame is built.
- A live light/dark toggle (`_toggle_theme`) switches the ttkbootstrap
  theme, persists the new preference, and rebuilds the current post-login
  view so every widget repaints in the new theme.
- Startup auto-login (D-01): a saved `auth_store.Session` is validated via
  the cheapest authenticated call, `GET /profile` (DB-only, no
  DeepSeek/MCP round trip) — a `401`/revoked token clears the session and
  falls back to the login screen (T-03-401); there is no client-side
  clock-expiry heuristic (the backend has none).
- `_after_login`: persists the just-logged-in session (D-01) and attaches
  the token to every subsequent `api_client` call before showing the main
  frame.
- `_logout` (T-03-LOGOUT): calls `POST /auth/logout` server-side FIRST to
  revoke the token, then clears the local session — in that order, and
  local clearing still happens even if the network call errors, so the
  token is never left server-valid-but-locally-gone.
"""

from __future__ import annotations

import tkinter as tk

from app import api_client, auth_store
from app.async_helpers import run_in_background
from app.ui import styles
from app.ui.login_frame import LoginFrame
from app.ui.main_frame import build_main_frame


def main() -> None:
    root = tk.Tk()
    root.title(styles.TITLE)
    root.geometry(styles.WINDOW_SIZE)
    root.minsize(*styles.MIN_SIZE)

    # `state` is a mutable holder so the nested closures below (_toggle_theme,
    # show_main) can read/reassign the active theme and current session.
    state: dict = {"theme": styles.load_theme_pref(), "session": None}
    styles.apply_theme(root, state["theme"])  # must run before any frame is built

    def show_login() -> None:
        for child in root.winfo_children():
            child.destroy()
        LoginFrame(root, on_success=_after_login).pack(fill="both", expand=True)

    def show_main(session: auth_store.Session) -> None:
        for child in root.winfo_children():
            child.destroy()
        state["session"] = session
        is_dark = state["theme"] == styles.THEME_DARK
        build_main_frame(
            root,
            session,
            on_logout=_logout,
            on_toggle_theme=_toggle_theme,
            is_dark=is_dark,
        ).pack(fill="both", expand=True)

    def _toggle_theme() -> None:
        new_theme = (
            styles.THEME_LIGHT if state["theme"] == styles.THEME_DARK else styles.THEME_DARK
        )
        styles.apply_theme(root, new_theme)
        styles.save_theme_pref(new_theme)
        state["theme"] = new_theme
        # Rebuild the current post-login view so freshly-built widgets pick
        # up the theme's updated surface colors (styles.COLOR_* globals are
        # read at widget-construction time). Note: an in-flight search's
        # results are lost on a manual theme toggle — accepted tradeoff.
        show_main(state["session"])

    def _after_login(session: auth_store.Session) -> None:
        auth_store.save_session(session)  # persist token for next launch (D-01)
        api_client.set_token(session.token)
        show_main(session)

    def _logout() -> None:
        def _finish_logout(_result) -> None:
            api_client.set_token(None)
            auth_store.clear_session()
            show_login()

        run_in_background(
            root,
            api_client.logout,  # server-side revocation FIRST (T-03-LOGOUT)
            on_success=_finish_logout,
            on_error=_finish_logout,  # clear locally even if the call errored
        )

    # Startup auto-login (D-01 / T-03-401).
    session = auth_store.load_session()
    if session is None:
        show_login()
    else:

        def _on_startup_valid(_profile) -> None:
            show_main(session)  # token still valid — skip login entirely

        def _on_startup_invalid(_exc) -> None:
            auth_store.clear_session()
            show_login()

        api_client.set_token(session.token)
        run_in_background(
            root,
            api_client.get_profile,
            on_success=_on_startup_valid,
            on_error=_on_startup_invalid,
        )

    root.mainloop()


if __name__ == "__main__":
    main()

"""Static-inspection tests for admin_tab.py's Excluir button + reveal-modal
centering wiring (quick-260711-x4h).

A real second `tk.Tk()` root reproduces the documented Windows/Tcl 8.6
flakiness (see test_main_frame.py / STATE.md Phase 03-06) — so, like
main_frame's Admin-tab-gating coverage, this verifies the hard-to-test UI
wiring by reading admin_tab.py's source and asserting on it directly,
matching this project's existing grep-based workaround. Kept Tk-root-free.
"""

import inspect

from app.ui import admin_tab

_SOURCE = inspect.getsource(admin_tab)


def test_excluir_button_label_exists():
    assert '"Excluir"' in _SOURCE


def test_own_row_guard_compares_against_session_user_id():
    assert 'user["user_id"] != self._session.user_id' in _SOURCE


def test_on_delete_click_calls_api_client_delete_user():
    on_delete_source = inspect.getsource(admin_tab.AdminTab._on_delete_click)
    assert "api_client.delete_user" in on_delete_source


def test_delete_confirmation_wording_is_severe():
    on_delete_source = inspect.getsource(admin_tab.AdminTab._on_delete_click)
    assert "PERMANENTE" in on_delete_source


def test_reveal_password_centers_over_parent_window():
    reveal_source = inspect.getsource(admin_tab.AdminTab._reveal_password)
    assert "update_idletasks" in reveal_source
    assert 'toplevel.geometry(f"+{x}+{y}")' in reveal_source


# ---------------------------------------------------------------------------
# Task 5 (quick-260712-1bx): reveal contrast + blank guard + Editar nome
# ---------------------------------------------------------------------------


def test_reveal_password_uses_classic_entry_with_explicit_contrast_colors():
    reveal_source = inspect.getsource(admin_tab.AdminTab._reveal_password)
    assert "fg=styles.COLOR_TEXT" in reveal_source
    assert "readonlybackground=" in reveal_source


def test_on_add_click_strips_and_blocks_blank_username():
    on_add_source = inspect.getsource(admin_tab.AdminTab._on_add_click)
    assert ".strip()" in on_add_source
    assert "Informe um nome de usuário." in on_add_source


def test_editar_nome_button_exists():
    assert '"Editar nome"' in _SOURCE


def test_on_rename_click_wires_api_client_rename_user():
    rename_source = inspect.getsource(admin_tab.AdminTab._on_rename_click)
    assert "api_client.rename_user" in rename_source
    assert "fg=styles.COLOR_TEXT" in rename_source

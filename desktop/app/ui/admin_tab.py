"""Admin tab: user list + add/deactivate/reset actions (D-05, DESKTOP-01).

`AdminTab` is the admin-only screen: it lists every user (username +
admin/inativo tags) and performs the four admin operations against the
existing backend endpoints (`GET/POST /auth/users`,
`PATCH .../deactivate`, `POST .../reset-password`) via `api_client`.

All backend authorization is enforced server-side by `require_admin`
(Phase 1) — this tab's own visibility (gated by `session.is_admin` in
`main_frame.py`, Plan 06) is UX convenience only (T-03-ADMIN, Pitfall 2).
A stray `403` here is handled the same way as any other error: surfaced
verbatim in the inline `Banner.TLabel`, never a crash.

Per 03-UI-SPEC.md's Error Display Contract, only two things ever use a
blocking `tkinter.messagebox` dialog: the destructive-action confirmations
(deactivate / reset password) and the one-time generated-password reveal.
Every other status/error uses the inline banner.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from app import api_client
from app.async_helpers import run_in_background
from app.ui import styles


class AdminTab(ttk.Frame):
    PASSWORD_REVEAL_TITLE = "Nova senha gerada"

    def __init__(self, parent, session):
        super().__init__(parent, style="Root.TFrame", padding=24)
        self._session = session
        self._users: list[dict] = []

        self._banner = ttk.Label(self, text="", style="Banner.TLabel", wraplength=800)
        # Hidden until an error occurs; packed on demand at the top of the
        # tab (before the add-user row), per the Error Display Contract.

        self._add_row = ttk.Frame(self, style="Root.TFrame")
        self._add_row.pack(fill="x", pady=(0, 16))

        self._username_entry = ttk.Entry(self._add_row)
        self._username_entry.pack(side="left", fill="x", expand=True)

        self._is_admin_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self._add_row, text="admin", variable=self._is_admin_var).pack(
            side="left", padx=(8, 0)
        )

        self._add_button = ttk.Button(
            self._add_row,
            text="Adicionar usuário",
            style="Accent.TButton",
            command=self._on_add_click,
        )
        self._add_button.pack(side="left", padx=(8, 0))

        self._list_frame = ttk.Frame(self, style="Root.TFrame")
        self._list_frame.pack(fill="both", expand=True)

        self._load_users()

    # --- data loading -----------------------------------------------

    def _load_users(self) -> None:
        run_in_background(
            self.winfo_toplevel(), api_client.list_users, self._render_users, self._on_error
        )

    def _render_users(self, users: list[dict]) -> None:
        self._users = users
        for child in self._list_frame.winfo_children():
            child.destroy()

        for user in users:
            self._render_user_row(user)

    def _render_user_row(self, user: dict) -> None:
        row = ttk.Frame(self._list_frame, style="Card.TFrame", padding=8)
        row.pack(fill="x", pady=(0, 8))

        label_text = user["username"]
        if user.get("is_admin"):
            label_text += "  [admin]"
        if not user.get("is_active", True):
            label_text += "  [inativo]"

        ttk.Label(row, text=label_text, background=styles.COLOR_SECONDARY).pack(
            side="left", fill="x", expand=True
        )

        # Permanent delete — hidden on the acting admin's own row (no
        # self-delete from the UI; the backend also refuses it, T-x4h).
        # Shown for every other row, active or inactive alike (unlike
        # Desativar/Reativar, which toggle based on state).
        if user["user_id"] != self._session.user_id:
            ttk.Button(
                row,
                text="Excluir",
                style="Destructive.TButton",
                command=lambda u=user: self._on_delete_click(u),
            ).pack(side="right", padx=(8, 0))

        if user.get("is_active", True):
            ttk.Button(
                row,
                text="Desativar",
                style="Destructive.TButton",
                command=lambda u=user: self._on_deactivate_click(u),
            ).pack(side="right", padx=(8, 0))
        else:
            ttk.Button(
                row,
                text="Reativar",
                style="Accent.TButton",
                command=lambda u=user: self._on_reactivate_click(u),
            ).pack(side="right", padx=(8, 0))

        ttk.Button(
            row,
            text="Gerar nova senha",
            command=lambda u=user: self._on_reset_click(u),
        ).pack(side="right")

        ttk.Button(
            row,
            text="Editar nome",
            command=lambda u=user: self._on_rename_click(u),
        ).pack(side="right", padx=(0, 8))

    # --- add user -----------------------------------------------------

    def _on_add_click(self) -> None:
        username = self._username_entry.get().strip()
        is_admin = self._is_admin_var.get()

        if not username:
            self._show_banner("Informe um nome de usuário.")
            return

        self._clear_banner()
        self._add_button.config(state="disabled")

        run_in_background(
            self.winfo_toplevel(),
            lambda: api_client.create_user(username, is_admin),
            self._on_user_created,
            self._on_error,
        )

    def _on_user_created(self, resp: dict) -> None:
        self._add_button.config(state="normal")
        self._username_entry.delete(0, "end")
        self._is_admin_var.set(False)
        self._reveal_password(resp["username"], resp["generated_password"])
        self._load_users()

    # --- deactivate -----------------------------------------------------

    def _on_deactivate_click(self, user: dict) -> None:
        confirmed = messagebox.askyesno(
            "Desativar usuário",
            f"Tem certeza que deseja desativar {user['username']}? "
            "O acesso será revogado imediatamente e a sessão ativa dele será encerrada.",
        )
        if not confirmed:
            return

        self._clear_banner()
        run_in_background(
            self.winfo_toplevel(),
            lambda: api_client.deactivate_user(user["user_id"]),
            self._on_mutation_ok,
            self._on_error,
        )

    def _on_mutation_ok(self, _resp: dict) -> None:
        self._load_users()

    # --- delete (permanent) -----------------------------------------------------

    def _on_delete_click(self, user: dict) -> None:
        confirmed = messagebox.askyesno(
            "Excluir usuário",
            "Esta ação é PERMANENTE e não pode ser desfeita. Excluir o usuário "
            f"'{user['username']}' e todo o seu histórico de buscas?",
        )
        if not confirmed:
            return

        self._clear_banner()
        run_in_background(
            self.winfo_toplevel(),
            lambda: api_client.delete_user(user["user_id"]),
            self._on_mutation_ok,
            self._on_error,
        )

    # --- reactivate -----------------------------------------------------

    def _on_reactivate_click(self, user: dict) -> None:
        confirmed = messagebox.askyesno(
            "Reativar usuário",
            f"Tem certeza que deseja reativar {user['username']}? "
            "O acesso será restaurado e ele(a) poderá fazer login novamente "
            "com a senha atual (ou a última gerada em um reset).",
        )
        if not confirmed:
            return

        self._clear_banner()
        run_in_background(
            self.winfo_toplevel(),
            lambda: api_client.reactivate_user(user["user_id"]),
            self._on_mutation_ok,
            self._on_error,
        )

    # --- reset password -----------------------------------------------------

    def _on_reset_click(self, user: dict) -> None:
        confirmed = messagebox.askyesno(
            "Gerar nova senha",
            f"Uma nova senha será gerada para {user['username']} e a senha atual "
            "deixará de funcionar. Deseja continuar?",
        )
        if not confirmed:
            return

        self._clear_banner()
        run_in_background(
            self.winfo_toplevel(),
            lambda: api_client.reset_password(user["user_id"]),
            lambda resp: self._on_password_reset(user, resp),
            self._on_error,
        )

    def _on_password_reset(self, user: dict, resp: dict) -> None:
        self._reveal_password(user["username"], resp["generated_password"])
        self._load_users()

    # --- rename (Editar nome) -----------------------------------------------------

    def _on_rename_click(self, user: dict) -> None:
        """Open a small modal to rename `user`, wired to api_client.rename_user.

        Mirrors `_reveal_password`'s Toplevel structure (transient, centered
        over the main window, grab_set) but with an EDITABLE `tk.Entry`
        pre-filled with the current username instead of a readonly field.
        """
        toplevel = tk.Toplevel(self)
        toplevel.title("Editar nome de usuário")
        toplevel.resizable(False, False)
        toplevel.transient(self.winfo_toplevel())

        container = ttk.Frame(toplevel, style="Root.TFrame", padding=16)
        container.pack(fill="both", expand=True)

        ttk.Label(
            container,
            text=f"Novo nome de usuário para {user['username']}:",
            background=styles.COLOR_DOMINANT,
        ).pack(anchor="w", pady=(0, 8))

        name_var = tk.StringVar(value=user["username"])
        name_entry = tk.Entry(
            container,
            textvariable=name_var,
            fg=styles.COLOR_TEXT,
            bg=styles.COLOR_SECONDARY,
            insertbackground=styles.COLOR_TEXT,
            font=styles.FONT_BODY,
        )
        name_entry.pack(fill="x", pady=(0, 12))

        button_row = ttk.Frame(container, style="Root.TFrame")
        button_row.pack(fill="x")

        def _on_salvar() -> None:
            new_name = name_var.get().strip()
            if not new_name:
                self._show_banner("Informe um nome de usuário.")
                return

            def _on_renamed(_resp: dict) -> None:
                toplevel.destroy()
                self._load_users()

            run_in_background(
                self.winfo_toplevel(),
                lambda: api_client.rename_user(user["user_id"], new_name),
                _on_renamed,
                self._on_error,
            )

        ttk.Button(
            button_row,
            text="Salvar",
            style="Accent.TButton",
            command=_on_salvar,
        ).pack(side="left")

        ttk.Button(
            button_row,
            text="Cancelar",
            command=toplevel.destroy,
        ).pack(side="left", padx=(8, 0))

        toplevel.update_idletasks()
        parent = self.winfo_toplevel()
        width = toplevel.winfo_reqwidth()
        height = toplevel.winfo_reqheight()
        x = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
        toplevel.geometry(f"+{x}+{y}")

        toplevel.grab_set()
        name_entry.focus_set()

    # --- shared helpers -----------------------------------------------------

    def _reveal_password(self, username: str, generated_password: str) -> None:
        """Show the one-time generated password in a small copy-to-clipboard modal.

        Used by both `_on_user_created` (new user) and `_on_password_reset`
        (password reset) reveals — a read-only, selectable field plus a
        "Copiar senha" button so the admin never has to hand-retype it.
        """
        toplevel = tk.Toplevel(self)
        toplevel.title(self.PASSWORD_REVEAL_TITLE)
        toplevel.resizable(False, False)
        toplevel.transient(self.winfo_toplevel())

        container = ttk.Frame(toplevel, style="Root.TFrame", padding=16)
        container.pack(fill="both", expand=True)

        ttk.Label(
            container,
            text=f"Senha para {username}:",
            background=styles.COLOR_DOMINANT,
        ).pack(anchor="w")

        ttk.Label(
            container,
            text="Anote ou copie agora — ela não será mostrada novamente.",
            background=styles.COLOR_DOMINANT,
        ).pack(anchor="w", pady=(0, 8))

        password_var = tk.StringVar(value=generated_password)
        password_entry = tk.Entry(
            container,
            textvariable=password_var,
            state="readonly",
            fg=styles.COLOR_TEXT,
            readonlybackground=styles.COLOR_SECONDARY,
            font=styles.FONT_BODY,
        )
        password_entry.pack(fill="x", pady=(0, 12))

        button_row = ttk.Frame(container, style="Root.TFrame")
        button_row.pack(fill="x")

        def _copy_password() -> None:
            toplevel.clipboard_clear()
            toplevel.clipboard_append(generated_password)
            toplevel.update()
            copy_button.config(text="Copiado!")

        copy_button = ttk.Button(
            button_row,
            text="Copiar senha",
            style="Accent.TButton",
            command=_copy_password,
        )
        copy_button.pack(side="left")

        ttk.Button(
            button_row,
            text="Fechar",
            command=toplevel.destroy,
        ).pack(side="left", padx=(8, 0))

        # Center over the main application window (not the OS-default
        # position) — must run AFTER the widgets above are built so
        # update_idletasks() can compute the dialog's real requested size.
        toplevel.update_idletasks()
        parent = self.winfo_toplevel()
        width = toplevel.winfo_reqwidth()
        height = toplevel.winfo_reqheight()
        x = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
        toplevel.geometry(f"+{x}+{y}")

        toplevel.grab_set()
        password_entry.focus_set()

    def _on_error(self, exc: Exception) -> None:
        self._add_button.config(state="normal")
        self._show_banner(getattr(exc, "detail", str(exc)))

    def _show_banner(self, text: str) -> None:
        self._banner.config(text=text)
        self._banner.pack(fill="x", pady=(0, 16), before=self._add_row)

    def _clear_banner(self) -> None:
        self._banner.config(text="")
        self._banner.pack_forget()

"""Testes unitários para ConcursoCard — botão "Copiar link" (ENTREGA-02).

Usa raiz Tk real com escopo de módulo (padrão estabelecido em test_busca_tab.py)
para evitar TclError no Windows ao criar/destruir múltiplos intérpretes Tcl.
Monkeypatching de clipboard via setattr direto no root Tk.
"""

import tkinter as tk

import pytest

from app.ui.concurso_card import ConcursoCard


@pytest.fixture(scope="module")
def _shared_root():
    r = tk.Tk()
    r.withdraw()
    yield r
    r.destroy()


@pytest.fixture
def root(_shared_root):
    yield _shared_root
    for child in _shared_root.winfo_children():
        child.destroy()


def test_copiar_link_chama_clipboard(root, monkeypatch):
    """_copiar_link() limpa o clipboard, appende a URL correta e exibe 'Copiado!'."""
    concurso = {
        "titulo": "Concurso Teste",
        "cargos": [],
        "datas": {},
        "noticia": {"link": "https://test.com/edital"},
        "is_new": False,
    }
    card = ConcursoCard(root, concurso)

    clear_calls = []
    append_calls = []

    tk_root = card.winfo_toplevel()
    monkeypatch.setattr(tk_root, "clipboard_clear", lambda: clear_calls.append(True))
    monkeypatch.setattr(
        tk_root, "clipboard_append", lambda text: append_calls.append(text)
    )

    card._copiar_link()

    assert len(clear_calls) == 1, "clipboard_clear deve ser chamado exatamente 1 vez"
    assert append_calls == [
        "https://test.com/edital"
    ], "clipboard_append deve receber a URL correta"
    assert (
        card._feedback_label.cget("text") == "Copiado!"
    ), "feedback label deve exibir 'Copiado!' após clicar"


def test_card_sem_link_sem_botao(root):
    """Cards sem link não devem ter _feedback_label nem botão 'Copiar link'."""
    concurso = {
        "titulo": "Concurso Sem Link",
        "cargos": [],
        "datas": {},
        "noticia": {"link": ""},
        "is_new": False,
    }
    card = ConcursoCard(root, concurso)

    assert not hasattr(
        card, "_feedback_label"
    ), "Card sem link não deve ter _feedback_label"
    assert not hasattr(
        card, "_copiar_link"
    ), "Card sem link não deve ter método _copiar_link"

    # Confirmar que nenhum widget filho tem text="Copiar link"
    def _get_all_widgets(widget):
        children = widget.winfo_children()
        result = list(children)
        for child in children:
            result.extend(_get_all_widgets(child))
        return result

    all_widgets = _get_all_widgets(card)
    copiar_texts = [
        w
        for w in all_widgets
        if hasattr(w, "cget") and _widget_text(w) == "Copiar link"
    ]
    assert len(copiar_texts) == 0, "Nenhum widget deve ter text='Copiar link' quando link está vazio"


def _widget_text(widget) -> str:
    """Retorna o text de um widget de forma segura, ou '' se não suportado."""
    try:
        return widget.cget("text")
    except Exception:
        return ""

"""qtbot tests para PerfilDialog (v1.1.0, Fase 6).

Exercita a lógica cumulativa dos checkboxes de formação, a habilitação dos
campos "qual?", a pré-população a partir de um perfil e o coletar() que monta
o body do PUT /profile. Não chama exec() (bloquearia) nem a rede — é widget
puro. `run_in_background` do main_window não entra aqui: o diálogo em si não
faz chamadas de rede.
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from app.ui.perfil_dialog import PerfilDialog


@pytest.fixture
def parent(qtbot):
    # MessageBoxBase reads parent.width()/height() in __init__, so the dialog
    # must have a real parent (in production it's always the main window).
    w = QWidget()
    w.resize(600, 700)
    qtbot.addWidget(w)
    return w


@pytest.fixture
def dialog(qtbot, parent):
    d = PerfilDialog({}, parent=parent)
    qtbot.addWidget(d)
    return d


# --- lógica cumulativa dos níveis ---------------------------------------


def test_checking_superior_auto_checks_medio_and_fundamental(dialog):
    dialog._checks["superior"].setChecked(True)
    assert dialog._checks["medio"].isChecked()
    assert dialog._checks["fundamental"].isChecked()


def test_checking_tecnico_auto_checks_medio_and_fundamental(dialog):
    dialog._checks["tecnico"].setChecked(True)
    assert dialog._checks["medio"].isChecked()
    assert dialog._checks["fundamental"].isChecked()


def test_unchecking_medio_unchecks_dependent_levels(dialog):
    dialog._checks["superior"].setChecked(True)
    dialog._checks["tecnico"].setChecked(True)
    assert dialog._checks["medio"].isChecked()

    dialog._checks["medio"].setChecked(False)
    assert not dialog._checks["superior"].isChecked()
    assert not dialog._checks["tecnico"].isChecked()


def test_unchecking_fundamental_clears_everything(dialog):
    dialog._checks["superior"].setChecked(True)
    dialog._checks["fundamental"].setChecked(False)
    for nivel in ("medio", "tecnico", "superior", "pos"):
        assert not dialog._checks[nivel].isChecked()


# --- campos "qual?" -----------------------------------------------------


def test_curso_field_enabled_only_when_level_checked(dialog):
    assert not dialog._cursos["superior"].isEnabled()
    dialog._checks["superior"].setChecked(True)
    assert dialog._cursos["superior"].isEnabled()


# --- coletar ------------------------------------------------------------


def test_coletar_builds_escolaridade_csv_in_order_and_nones_blanks(dialog):
    dialog._checks["superior"].setChecked(True)  # implica medio + fundamental
    dialog._cursos["superior"].setText("Enfermagem")

    campos = dialog.coletar()
    assert campos["escolaridade"] == "fundamental,medio,superior"
    assert campos["graduacao"] == "Enfermagem"
    assert campos["tecnico"] is None
    assert campos["cidade"] is None  # em branco -> None


def test_coletar_ignores_curso_text_when_level_unchecked(dialog):
    # texto digitado mas o nível técnico NÃO está marcado -> não coletado
    dialog._cursos["tecnico"].setEnabled(True)
    dialog._cursos["tecnico"].setText("TDS")
    campos = dialog.coletar()
    assert campos["tecnico"] is None


def test_coletar_empty_form_is_all_none(dialog):
    campos = dialog.coletar()
    assert all(v is None for v in campos.values())


# --- pré-popular --------------------------------------------------------


def test_prepopulate_restores_checkboxes_fields_and_round_trips(qtbot, parent):
    perfil = {
        "graduacao": "Enfermagem",
        "tecnico": None,
        "pos_graduacao": None,
        "escolaridade": "fundamental,medio,superior",
        "formacao_futura": "Mestrado",
        "cep": "13010-111",
        "uf": "SP",
        "cidade": "Campinas",
        "mobilidade": "estado",
        "areas_interesse": "saúde",
        "experiencia": "3 anos em UBS",
        "curriculo": "meu currículo em texto",
    }
    d = PerfilDialog(perfil, parent=parent)
    qtbot.addWidget(d)

    assert d._checks["superior"].isChecked()
    assert d._checks["medio"].isChecked()
    assert d._cursos["superior"].text() == "Enfermagem"
    assert d._uf.currentText() == "SP"
    assert d._cidade.text() == "Campinas"
    assert d._cep.text() == "13010-111"
    assert d._curriculo.toPlainText() == "meu currículo em texto"

    campos = d.coletar()
    assert campos["graduacao"] == "Enfermagem"
    assert campos["escolaridade"] == "fundamental,medio,superior"
    assert campos["cep"] == "13010-111"
    assert campos["uf"] == "SP"
    assert campos["mobilidade"] == "estado"
    assert campos["formacao_futura"] == "Mestrado"
    assert campos["areas_interesse"] == "saúde"
    # Experiência foi removida do formulário (o currículo cobre isso).
    assert "experiencia" not in campos


# --- data de formação (v1.4.0) ------------------------------------------


def test_prepopulate_data_formacao_futura_shows_mmaaaa(qtbot, parent):
    d = PerfilDialog({"data_formacao_futura": "2027-12"}, parent=parent)
    qtbot.addWidget(d)
    assert d._data_formacao_futura.text() == "12/2027"


def test_prepopulate_sem_data_formacao_futura_deixa_campo_vazio(dialog):
    assert dialog._data_formacao_futura.text() == ""


def test_coletar_converte_data_para_iso(dialog):
    dialog._data_formacao_futura.setText("12/2027")
    campos = dialog.coletar()
    assert campos["data_formacao_futura"] == "2027-12"


def test_coletar_data_vazia_vira_none(dialog):
    campos = dialog.coletar()
    assert campos["data_formacao_futura"] is None


@pytest.mark.parametrize("invalido", ["13/2027", "2027", "abc", "00/2027"])
def test_validate_data_invalida_bloqueia_e_mostra_erro(dialog, monkeypatch, invalido):
    from app.ui import perfil_dialog as mod

    erros = []
    monkeypatch.setattr(
        mod.InfoBar, "error", lambda **kwargs: erros.append(kwargs.get("content"))
    )
    dialog._data_formacao_futura.setText(invalido)
    assert dialog.validate() is False
    assert erros and "MM/AAAA" in erros[0]


def test_validate_data_valida_ou_vazia_passa(dialog):
    assert dialog.validate() is True
    dialog._data_formacao_futura.setText("12/2027")
    assert dialog.validate() is True


def test_cep_autofill_fills_cidade_and_uf(dialog, monkeypatch):
    from app.ui import perfil_dialog as mod

    monkeypatch.setattr(mod, "run_in_background", lambda fn, ok, err: ok(fn()))
    monkeypatch.setattr(
        mod.api_client, "lookup_cep", lambda cep: {"cidade": "Recife", "uf": "PE"}
    )

    dialog._cep.setText("50000-000")
    dialog._on_buscar_cep()

    assert dialog._cidade.text() == "Recife"
    assert dialog._uf.currentText() == "PE"


def test_cep_error_shows_status_and_reenables(dialog, monkeypatch):
    from app.ui import perfil_dialog as mod

    monkeypatch.setattr(mod, "run_in_background", lambda fn, ok, err: err(_FakeApiError()))
    dialog._cep.setText("50000000")
    dialog._on_buscar_cep()

    assert dialog._cep_button.isEnabled()
    assert "não" in dialog._cep_status.text().lower() or dialog._cep_status.text()


def test_anexar_curriculo_fills_textedit_and_switches_to_anexado(dialog, monkeypatch):
    from app.ui import perfil_dialog as mod

    monkeypatch.setattr(
        mod.QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: ("/tmp/cv.txt", ""))
    )
    monkeypatch.setattr(mod.curriculo, "extrair_texto", lambda caminho: "texto do cv")

    dialog._on_anexar_curriculo()
    assert dialog._curriculo.toPlainText() == "texto do cv"
    # Anexar troca para o estado B (ações Visualizar/Alterar/Excluir).
    assert dialog._curriculo_anexado is True


def test_excluir_curriculo_clears_and_returns_to_estado_a(dialog, monkeypatch):
    from app.ui import perfil_dialog as mod

    monkeypatch.setattr(
        mod.QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: ("/tmp/cv.txt", ""))
    )
    monkeypatch.setattr(mod.curriculo, "extrair_texto", lambda caminho: "texto do cv")
    dialog._on_anexar_curriculo()

    dialog._on_excluir_curriculo()
    assert dialog._curriculo.toPlainText() == ""
    assert dialog._curriculo_anexado is False
    # coletar não deve mais mandar currículo
    assert dialog.coletar()["curriculo"] is None


def test_prepopulate_with_curriculo_starts_anexado(qtbot, parent):
    d = PerfilDialog({"curriculo": "meu cv salvo"}, parent=parent)
    qtbot.addWidget(d)
    assert d._curriculo_anexado is True
    assert d.coletar()["curriculo"] == "meu cv salvo"


def test_visualizar_curriculo_opens_attached_file(dialog, monkeypatch, tmp_path):
    """Com um arquivo anexado nesta sessão, "Visualizar" abre o arquivo COMO ELE
    É no visualizador padrão (QDesktopServices.openUrl), não o texto extraído."""
    from app.ui import perfil_dialog as mod

    f = tmp_path / "cv.pdf"
    f.write_text("conteudo")
    opened = []
    monkeypatch.setattr(
        mod.QDesktopServices, "openUrl", staticmethod(lambda url: opened.append(url))
    )
    dialog._curriculo_path = str(f)

    dialog._on_ver_curriculo()
    assert len(opened) == 1


def test_visualizar_sem_arquivo_alterna_texto(dialog, monkeypatch):
    """Sem arquivo (texto colado/salvo), "Visualizar" alterna o texto e NÃO
    tenta abrir nada externamente."""
    from app.ui import perfil_dialog as mod

    opened = []
    monkeypatch.setattr(
        mod.QDesktopServices, "openUrl", staticmethod(lambda url: opened.append(url))
    )
    dialog._curriculo_path = None
    dialog._on_ver_curriculo()
    assert opened == []


class _FakeApiError(Exception):
    detail = "Não foi possível consultar o CEP."


# --- máscara MM/AAAA no campo de data de formação (v1.5.2) --------------


def test_mascara_digitar_seis_digitos_insere_barra(qtbot, dialog):
    qtbot.keyClicks(dialog._data_formacao_futura, "122027")
    assert dialog._data_formacao_futura.text() == "12/2027"


def test_mascara_digitar_dois_digitos_mostra_barra_pendente(qtbot, dialog):
    qtbot.keyClicks(dialog._data_formacao_futura, "12")
    assert dialog._data_formacao_futura.text() == "12/"


def test_mascara_filtra_caracteres_nao_digitos(qtbot, dialog):
    # Letras nunca entram no campo; com 2 dígitos válidos digitados ("1", "2"),
    # a barra já foi inserida automaticamente antes da letra final ser filtrada.
    qtbot.keyClicks(dialog._data_formacao_futura, "1a2b")
    assert dialog._data_formacao_futura.text() == "12/"


def test_mascara_limita_a_seis_digitos(qtbot, dialog):
    qtbot.keyClicks(dialog._data_formacao_futura, "12202799")
    assert dialog._data_formacao_futura.text() == "12/2027"


def test_mascara_backspace_nao_trava(qtbot, dialog):
    qtbot.keyClicks(dialog._data_formacao_futura, "122027")
    assert dialog._data_formacao_futura.text() == "12/2027"

    qtbot.keyClick(dialog._data_formacao_futura, Qt.Key_Backspace)
    # Não deve travar/crashar; o texto continua só com dígitos + barra opcional.
    texto = dialog._data_formacao_futura.text()
    assert all(c.isdigit() or c == "/" for c in texto)

    dialog._data_formacao_futura.clear()
    assert dialog._data_formacao_futura.text() == ""


def test_mascara_nao_quebra_validacao_e_coleta_existentes(qtbot, dialog):
    """A máscara não deve interferir em validate()/coletar() já cobertos
    acima — digitar via máscara produz o mesmo resultado que setText direto."""
    qtbot.keyClicks(dialog._data_formacao_futura, "122027")
    assert dialog.validate() is True
    assert dialog.coletar()["data_formacao_futura"] == "2027-12"

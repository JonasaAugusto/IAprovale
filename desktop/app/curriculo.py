"""Extração de texto de currículo a partir de um arquivo (PDF ou TXT) — v1.1.0.

Usado pelo botão "Anexar" do diálogo de perfil: o usuário escolhe um arquivo,
extraímos o texto AQUI (barato, sem gastar token) e preenchemos o campo de
texto do currículo. O uso do texto pela IA na busca é uma etapa posterior.

`pypdf` é Python puro (sem DLL) — empacota limpo no `.exe` (mesma linha do
`fpdf2`). PDFs escaneados (imagem, sem camada de texto) não têm texto a
extrair: nesse caso levantamos `CurriculoVazioError` com uma mensagem clara,
em vez de devolver string vazia silenciosamente.
"""

from __future__ import annotations

from pathlib import Path

# Limite de caracteres do texto extraído — espelha o max_length do campo
# `curriculo` no backend (5000), truncando aqui antes de exibir/enviar.
MAX_CHARS = 5000

EXTENSOES_SUPORTADAS = (".pdf", ".txt")


class CurriculoError(Exception):
    """Falha ao ler/So extrair o arquivo de currículo (mensagem PT-BR pronta)."""


class CurriculoVazioError(CurriculoError):
    """O arquivo abriu mas não tinha texto extraível (ex: PDF escaneado)."""


def _normalizar(texto: str) -> str:
    # Colapsa espaços/linhas em excesso e trunca no limite.
    linhas = [ln.strip() for ln in texto.splitlines()]
    texto = "\n".join(ln for ln in linhas if ln)
    return texto[:MAX_CHARS].strip()


def extrair_texto(caminho: str) -> str:
    """Devolve o texto do arquivo (.pdf ou .txt). Levanta CurriculoError com
    mensagem amigável em qualquer falha — o chamador mostra num InfoBar."""
    path = Path(caminho)
    ext = path.suffix.lower()

    if ext not in EXTENSOES_SUPORTADAS:
        raise CurriculoError("Formato não suportado. Envie um PDF ou um TXT.")

    if ext == ".txt":
        try:
            bruto = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise CurriculoError("Não consegui ler o arquivo.") from exc
        texto = _normalizar(bruto)
        if not texto:
            raise CurriculoVazioError("O arquivo está vazio.")
        return texto

    # PDF
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependência sempre presente
        raise CurriculoError("Suporte a PDF indisponível nesta instalação.") from exc

    try:
        reader = PdfReader(str(path))
        partes = [(page.extract_text() or "") for page in reader.pages]
    except Exception as exc:  # pypdf pode levantar vários tipos (arquivo corrompido/protegido)
        raise CurriculoError(
            "Não consegui ler esse PDF (pode estar corrompido ou protegido). "
            "Tente outro arquivo ou cole o texto."
        ) from exc

    texto = _normalizar("\n".join(partes))
    if not texto:
        raise CurriculoVazioError(
            "Não encontrei texto nesse PDF (parece ser digitalizado/imagem). "
            "Cole o texto do currículo manualmente."
        )
    return texto

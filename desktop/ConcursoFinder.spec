# ConcursoFinder.spec
# Build: cd desktop && .venv/Scripts/python -m PyInstaller ConcursoFinder.spec --noconfirm
from PyInstaller.utils.hooks import collect_all, collect_data_files

# qfluentwidgets: sem hook nativo em pyinstaller-hooks-contrib — coleta manual
# de QSS/icones/fontes (05-RESEARCH.md Pitfall 2).
qfw_datas, qfw_binaries, qfw_hidden = collect_all("qfluentwidgets")

# qframelesswindow: dependencia transitiva do qfluentwidgets (janela sem borda
# usada internamente por alguns componentes) — coleta defensiva, per 05-RESEARCH.md
# Pitfall 2 mitigacao 3 / Assumption A2. Se um build real mostrar que nao e
# necessario, remover.
qfl_datas, qfl_binaries, qfl_hidden = collect_all("qframelesswindow")

# certifi: hook nativo existe, mas incluimos explicitamente para visibilidade
# (evita SSLError em maquina limpa por CA roots ausentes — T-05-SSL).
certifi_datas = collect_data_files("certifi")

a = Analysis(
    ["app/main.py"],
    pathex=["."],
    binaries=qfw_binaries + qfl_binaries,
    datas=qfw_datas + qfl_datas + certifi_datas,
    hiddenimports=qfw_hidden + qfl_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ConcursoFinder",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # --noupx: AV mitigation (T-05-AV)
    console=False,      # --noconsole: app GUI, sem terminal
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ConcursoFinder",
)

# concurso_finder.spec
# Build: cd desktop && .venv/Scripts/pyinstaller concurso_finder.spec
from PyInstaller.utils.hooks import collect_all, collect_data_files

# ttkbootstrap: sem hook nativo em pyinstaller-hooks-contrib 2026.6
tb_datas, tb_binaries, tb_hidden = collect_all("ttkbootstrap")

# certifi: hook nativo existe, mas incluimos explicitamente para visibilidade
certifi_datas = collect_data_files("certifi")

a = Analysis(
    ["app/main.py"],
    pathex=["."],
    binaries=tb_binaries,
    datas=tb_datas + certifi_datas,
    hiddenimports=tb_hidden,
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
    upx=False,          # --noupx: AV mitigation (T-04-AV)
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

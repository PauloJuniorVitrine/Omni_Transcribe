# -*- mode: python; coding: utf-8 -*-

"""
PyInstaller spec for TranscribeFlow.
- pathex inclui src/ para resolver imports de interfaces/http/etc.
- datas embute templates, assets estáticos e perfis de prompt.
"""

block_cipher = None

pathex = [".", "src"]
datas = [
    ("src/interfaces/web/templates", "interfaces/web/templates"),
    ("src/interfaces/web/static", "interfaces/web/static"),
    ("profiles", "profiles"),
]

a = Analysis(
    ["launcher_gui.py"],
    pathex=pathex,
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="TranscribeFlow",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[],
)

# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

# apprise descobre seus plugins de notificacao varrendo o diretorio do
# pacote em tempo de execucao (nao por import estatico), entao o
# PyInstaller nao os enxerga sozinho e precisam ser coletados a mao.
apprise_datas, apprise_binaries, apprise_hiddenimports = collect_all('apprise')
# pygrabber usa comtypes, que gera wrappers COM em tempo de execucao.
comtypes_datas, comtypes_binaries, comtypes_hiddenimports = collect_all('comtypes')

a = Analysis(
    ['src\\main.py'],
    pathex=[],
    binaries=apprise_binaries + comtypes_binaries,
    datas=[('models', 'models'), ('assets/icon.png', 'assets')] + apprise_datas + comtypes_datas,
    hiddenimports=['pystray._win32', 'pygrabber.dshow_graph']
    + apprise_hiddenimports + comtypes_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='X9',
    icon='assets\\icon.ico',
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
)

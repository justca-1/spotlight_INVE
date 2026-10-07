# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for Spotlight. Build with:
#     pyinstaller spotlight.spec
#
# The critical line is `datas=[('assets', 'assets')]` below -- without it,
# the app builds and runs without crashing, but silently loses its entire
# dark theme and bundled font, because PyInstaller's static analysis has
# no way to know app/main.py reads assets/style.qss and
# assets/fonts/Inter.ttf via a runtime Path() lookup. This was confirmed
# with an actual test build, not just predicted -- see build_exe.md for
# the full writeup.

a = Analysis(
    ['app/main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets')],
    hiddenimports=[],
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
    [],
    exclude_binaries=True,
    name='Spotlight',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Spotlight',
)

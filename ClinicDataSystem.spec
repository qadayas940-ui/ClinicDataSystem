# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hidden = collect_submodules("django") + collect_submodules("apps") + ["config.settings.production"]

a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=[],
    datas=[("templates", "templates"), ("static", "static")],
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter.test", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ClinicDataSystem",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
coll = COLLECT(a.binaries, a.datas, exe, name="ClinicDataSystem")

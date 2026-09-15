# -*- mode: python ; coding: utf-8 -*-
import os

from PyInstaller.utils.hooks import collect_submodules

# The Django PyInstaller hook imports the configured settings while analysing
# the bundle. Point it at test settings for build-time discovery only;
# launcher.py selects production settings when the installed app starts.
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.testing"

hidden = (
    collect_submodules("django")
    + collect_submodules("apps")
    + collect_submodules("whitenoise")
    + ["config.settings.production", "whitenoise.storage"]
)

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

# PyInstaller spec — forgeimages-bridge sidecar (onefile).
#
# One binary that carries the FastAPI bridge, the forgeimages-cli engine and the
# template contracts. packaging/build.sh builds the CLI first and passes its path
# in FORGEIMAGES_CLI_BUILD.
#
# Layout inside the archive (sys._MEIPASS):
#   bridge/                  the FastAPI bridge package
#   forgeimages-cli[.exe]    the Rust engine the bridge calls
#   templates/               forgeimages-core/templates, the template contracts

import os

from PyInstaller.utils.hooks import collect_submodules

repo_root = os.path.dirname(SPECPATH)
cli_build = os.environ["FORGEIMAGES_CLI_BUILD"]

hiddenimports = []
hiddenimports += collect_submodules("uvicorn")
hiddenimports += collect_submodules("fastapi")
hiddenimports += collect_submodules("pydantic_settings")
hiddenimports += collect_submodules("bridge")

a = Analysis(
    [os.path.join(SPECPATH, "freeze_entry.py")],
    pathex=[os.path.join(repo_root, "forgeagents-forgeimages")],
    binaries=[(cli_build, ".")],
    datas=[(os.path.join(repo_root, "forgeimages-core", "templates"), "templates")],
    hiddenimports=hiddenimports,
    excludes=["tkinter", "httpx", "skill"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="forgeimages-bridge",
    debug=False,
    strip=False,
    upx=False,
    console=True,
)

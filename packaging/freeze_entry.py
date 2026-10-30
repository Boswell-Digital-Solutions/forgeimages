"""PyInstaller entrypoint for the forgeimages-bridge sidecar.

AuthorForge ships the ForgeImages bridge as a Tauri-managed sidecar: one frozen
binary that carries the bridge, the ``forgeimages-cli`` engine and the template
contracts, all from one ForgeImages commit. NeuronForge Local's image lane sends
every diffusion master to it (``FORGEIMAGES_URL``, registered port 8100).

Inside the binary the CLI and the templates are at ``sys._MEIPASS``. They are the
defaults for ``FORGEIMAGES_CLI_PATH`` and ``FORGEIMAGES_TEMPLATES_DIR``; an
explicit environment value still wins. The bridge writes an append-only audit log,
and a frozen binary has no sensible working directory for it, so
``FORGEIMAGES_AUDIT_LOG_PATH`` is required: without it the binary exits 2 and
names the variable.

Host and port come from ``FORGEIMAGES_BRIDGE_HOST`` / ``FORGEIMAGES_BRIDGE_PORT``,
default ``127.0.0.1:8100``.

``--runtime-info`` prints one JSON object (interpreter, platform, frozen state,
the import result of every module the bridge needs, and the template list the
bundled CLI reports) and exits. It opens no socket and writes no file.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REQUIRED_MODULES = (
    "fastapi",
    "pydantic",
    "pydantic_settings",
    "uvicorn",
)

CLI_NAME = "forgeimages-cli" + (".exe" if os.name == "nt" else "")


def _bundle_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def _default_engine_env() -> None:
    root = _bundle_root()
    os.environ.setdefault("FORGEIMAGES_CLI_PATH", str(root / CLI_NAME))
    os.environ.setdefault("FORGEIMAGES_TEMPLATES_DIR", str(root / "templates"))


def _engine_report() -> dict:
    """Run the bundled CLI's `templates` command. ok only when it lists templates."""
    import json
    import subprocess

    cli = os.environ["FORGEIMAGES_CLI_PATH"]
    templates = os.environ["FORGEIMAGES_TEMPLATES_DIR"]
    try:
        result = subprocess.run(
            [cli, "--templates-dir", templates, "templates"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        ids = sorted(t["id"] for t in json.loads(result.stdout)) if result.returncode == 0 else []
        error = None if result.returncode == 0 else (result.stderr or result.stdout).strip()[:500]
    except Exception as exc:  # report the cause, then fail closed
        ids, error = [], f"{type(exc).__name__}: {exc}"
    return {"engine": {"templates": ids, "error": error}, "ok": bool(ids) and error is None}


def _runtime_info() -> int:
    import importlib
    import json
    import platform

    modules: dict[str, str] = {}
    for module in REQUIRED_MODULES:
        try:
            importlib.import_module(module)
            modules[module] = "ok"
        except Exception as exc:
            modules[module] = f"{type(exc).__name__}: {exc}"
    report = {
        "name": "forgeimages-bridge",
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "system": platform.system(),
        "machine": platform.machine(),
        "frozen": bool(getattr(sys, "frozen", False)),
        "modules": modules,
    }
    engine = _engine_report()
    report.update(engine)
    report["ok"] = all(state == "ok" for state in modules.values()) and engine["ok"]
    print(json.dumps(report, sort_keys=True))
    return 0 if report["ok"] else 1


def main() -> int:
    if not os.environ.get("FORGEIMAGES_AUDIT_LOG_PATH"):
        print(
            "forgeimages-bridge: FORGEIMAGES_AUDIT_LOG_PATH is not set; the bridge "
            "keeps an append-only audit log and will not guess where to write it",
            file=sys.stderr,
        )
        return 2

    import uvicorn

    from bridge.forgeimages_bridge import app

    host = os.environ.get("FORGEIMAGES_BRIDGE_HOST", "127.0.0.1")
    if host not in {"127.0.0.1", "::1", "localhost"}:
        print(
            "forgeimages-bridge: loopback-only; FORGEIMAGES_BRIDGE_HOST must be "
            "127.0.0.1, ::1 or localhost",
            file=sys.stderr,
        )
        return 2
    port = int(os.environ.get("FORGEIMAGES_BRIDGE_PORT", "8100"))
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0


if __name__ == "__main__":
    _default_engine_env()
    if sys.argv[1:] == ["--runtime-info"]:
        sys.exit(_runtime_info())
    if sys.argv[1:]:
        print(
            f"forgeimages-bridge: unknown arguments {sys.argv[1:]!r}; only --runtime-info is accepted",
            file=sys.stderr,
        )
        sys.exit(2)
    sys.exit(main())

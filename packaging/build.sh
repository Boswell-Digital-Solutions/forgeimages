#!/usr/bin/env bash
#
# Build the ForgeImages bridge sidecar as one frozen binary (PyInstaller onefile)
# that carries the bridge, the forgeimages-cli engine and the templates.
# AuthorForge consumes it as a Tauri externalBin.
#
#   Output: packaging/dist/forgeimages-bridge[.exe]
#
# Usage:
#   packaging/build.sh
#   TARGET_TRIPLE=x86_64-unknown-linux-gnu packaging/build.sh
#       # also copy the artifact to packaging/dist/forgeimages-bridge-<triple>[.exe]
#   PYTHON=/path/to/python3.12 packaging/build.sh
#
# Runs on Linux, macOS and Windows (Git Bash). Needs cargo and CPython 3.12.
# Rust dependencies come from the tracked Cargo.lock, Python dependencies only
# from the hashed lock packaging/requirements-freeze.txt.
# The build ends with --runtime-info, which runs the bundled CLI.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
cd "$ROOT"
# shellcheck source=packaging/freeze_env.sh
. "$HERE/freeze_env.sh"

freeze_platform
freeze_venv "$ROOT/.venv-freeze" "$HERE/requirements-freeze.txt"
freeze_require_python
"$VENV_PY" -m pip check

# --locked: the shipped engine builds from the tracked Cargo.lock, never from a fresh resolve.
cargo build --release --locked -p forgeimages-core --bin forgeimages-cli
FORGEIMAGES_CLI_BUILD="$ROOT/target/release/forgeimages-cli$EXE"
[ -f "$FORGEIMAGES_CLI_BUILD" ] || { echo "[build] ERROR: $FORGEIMAGES_CLI_BUILD was not produced" >&2; exit 1; }
export FORGEIMAGES_CLI_BUILD

"$VENV_PY" -m PyInstaller packaging/forgeimages-bridge.spec --clean --noconfirm \
  --distpath packaging/dist --workpath packaging/build

BIN="packaging/dist/forgeimages-bridge$EXE"
freeze_self_check "$BIN"
echo "[build] built: $BIN"

if [ -n "${TARGET_TRIPLE:-}" ]; then
  cp "$BIN" "packaging/dist/forgeimages-bridge-${TARGET_TRIPLE}$EXE"
  echo "[build] tauri sidecar copy: packaging/dist/forgeimages-bridge-${TARGET_TRIPLE}$EXE"
fi

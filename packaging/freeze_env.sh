# Sourced by packaging/build.sh. Source it; do not run it. Copied from
# forge-neuronforge packaging/freeze_env.sh so every AuthorForge sidecar freezes the same way.
#
# Provides a freeze environment that is reproducible on Linux, macOS and Windows
# (Git Bash / MSYS):
#   freeze_platform            sets VENV_BIN (bin|Scripts) and EXE ("" | ".exe")
#   freeze_venv <venv> <lock>  (re)creates <venv> from <lock> with --require-hashes,
#                              only when the venv is missing or the lock changed;
#                              sets VENV_PY
#   freeze_require_python      fails unless VENV_PY is CPython $REQUIRED_PYTHON
#   freeze_self_check <bin>    runs "<bin> --runtime-info" and fails unless it exits 0
#
# PYTHON selects the interpreter that creates the venv (default python3).

REQUIRED_PYTHON="3.12"

freeze_platform() {
  case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*) VENV_BIN="Scripts"; EXE=".exe" ;;
    *) VENV_BIN="bin"; EXE="" ;;
  esac
  PYTHON="${PYTHON:-python3}"
}

freeze_venv() {
  local venv="$1" lock="$2" stamp lock_hash
  stamp="$venv/.freeze-lock.sha256"
  VENV_PY="$venv/$VENV_BIN/python$EXE"
  lock_hash="$("$PYTHON" -c 'import hashlib, sys; print(hashlib.sha256(open(sys.argv[1], "rb").read().replace(b"\r\n", b"\n")).hexdigest())' "$lock")"
  if [ -x "$VENV_PY" ] && [ "$(cat "$stamp" 2>/dev/null || true)" = "$lock_hash" ]; then
    return 0
  fi
  echo "[build] creating freeze venv at $venv from $(basename "$lock")"
  rm -rf "$venv"
  "$PYTHON" -m venv "$venv"
  "$VENV_PY" -m pip install -q --disable-pip-version-check --require-hashes --no-deps -r "$lock"
  echo "$lock_hash" > "$stamp"
}

freeze_require_python() {
  local actual
  actual="$("$VENV_PY" -c 'import platform; print(platform.python_version())')"
  case "$actual" in
    "$REQUIRED_PYTHON".*) ;;
    *)
      echo "[build] ERROR: freeze venv runs Python $actual; these sidecars are built with $REQUIRED_PYTHON." >&2
      echo "[build] Set PYTHON to a CPython $REQUIRED_PYTHON interpreter." >&2
      return 1
      ;;
  esac
}

freeze_self_check() {
  local bin="$1"
  [ -f "$bin" ] || { echo "[build] ERROR: $bin was not produced" >&2; return 1; }
  echo "[build] self-check: $bin --runtime-info"
  "$bin" --runtime-info
}

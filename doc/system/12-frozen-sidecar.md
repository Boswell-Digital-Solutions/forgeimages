# §12 — Frozen Bridge Sidecar

AuthorForge release bundles ship the bridge as one frozen binary,
`forgeimages-bridge`. NeuronForge Local's image lane sends every diffusion
master to it at `FORGEIMAGES_URL` (registered port 8100).

## What the binary carries

`packaging/build.sh` builds one PyInstaller onefile binary from one commit. It
holds three parts:

| Part | Source | Location in the archive |
| --- | --- | --- |
| The FastAPI bridge | `forgeagents-forgeimages/bridge/` | `bridge/` |
| The engine | `forgeimages-cli`, built with `cargo build --release --locked` | archive root |
| The template contracts | `forgeimages-core/templates/` | `templates/` |

The bridge, the engine and the templates therefore always come from the same
ForgeImages commit. The agent skill and `httpx` are not in the binary.

## Reproducibility

- Rust dependencies come from the tracked `Cargo.lock`. The build uses `--locked`.
- Python dependencies come only from the hashed universal lock
  `packaging/requirements-freeze.txt`, installed with `--require-hashes`.
- The build requires CPython 3.12. `packaging/freeze_env.sh` is the same helper
  that forge-neuronforge uses for the other AuthorForge sidecars.

## Runtime contract

| Variable | Default | Meaning |
| --- | --- | --- |
| `FORGEIMAGES_BRIDGE_HOST` | `127.0.0.1` | Bind address |
| `FORGEIMAGES_BRIDGE_PORT` | `8100` | Bind port |
| `FORGEIMAGES_AUDIT_LOG_PATH` | none, **required** | Append-only audit log. Without it the binary exits 2 and names the variable |
| `FORGEIMAGES_CLI_PATH` | the bundled CLI | Override the engine |
| `FORGEIMAGES_TEMPLATES_DIR` | the bundled templates | Override the template contracts |

`forgeimages-bridge --runtime-info` prints one JSON object and exits. It reports
the interpreter, the platform, the frozen state, the import result of each
required module, and the template list that the bundled CLI returns. It opens no
socket and writes no file. It exits 0 only when every part works. Any other
argument exits 2.

The bridge does not require a per-launch capability. It binds to loopback only, which does not stop a local browser page from calling it (KI-IMG-20261030-001, open).

## Qualification

`packaging/qualify_frozen.py` runs the binary and checks the runtime report, the
refusals, `/health`, `/templates`, a compile of a 1080×1080 noise master of more
than 4 MiB, the audit line, and the teardown. `.github/workflows/freeze.yml` runs
the engine tests, the build and the qualification on ubuntu-22.04, macos-latest
and windows-latest.

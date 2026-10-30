# §3 — Tech Stack

## Rust Core Engine

| Dependency | Version | Purpose |
|------------|---------|---------|
| serde | 1.0 (features: derive) | Serialization/deserialization |
| serde_json | 1.0 | JSON parsing and canonical output |
| sha2 | 0.10 | SHA-256 manifest hashing |
| semver | 1.0 (features: serde) | Template version compatibility |
| thiserror | 1.0 | Typed error handling |
| base64 | 0.21 | Export data encoding |
| chrono | 0.4 (features: serde) | Timestamps |
| uuid | 1.0 (features: v4, serde) | Asset and export IDs |
| clap | 4.0 (features: derive) | CLI argument parsing |
| image | 0.25 (no default features; jpeg, png, tiff) | Raster decode, resize (Lanczos3) and encode for source masters and file validation |
| tempfile | 3.0 (dev only) | Test fixtures |

**Rust edition:** 2024 (workspace `resolver = "3"`)
**MSRV:** Follows Rust 2024 edition requirements
**Lockfile:** `Cargo.lock` is tracked and release builds use `--locked` (KI-IMG-20261017-002)

The PDF/X-1a writer (`pdf.rs`) uses no PDF library and no compressor. That is deliberate, for byte-reproducibility (§8).

## Tauri Integration Crate

| Dependency | Version | Purpose |
|------------|---------|---------|
| forgeimages-core | path | The engine |
| tauri | 2 (no default features) | `#[tauri::command]` and managed state |
| serde | 1.0 | IPC payloads |
| image | 0.25 (jpeg, png, tiff) | File decoding |

## Python Bridge + Skill

| Dependency | Version | Purpose |
|------------|---------|---------|
| fastapi | >=0.104.0 | HTTP bridge framework |
| uvicorn[standard] | >=0.24.0 | ASGI server |
| pydantic | >=2.5.0 | Request/response validation |
| pydantic-settings | >=2.1.0 | Environment-based configuration |
| httpx | >=0.25.0 | Async HTTP client (skill → bridge) |
| pytest | >=7.4.0 (dev) | Test framework |
| pytest-asyncio | >=0.21.0 (dev) | Async test support |

**Python version:** >=3.10
**Build system:** hatchling

## Frozen Sidecar Build

| Input | Version | Purpose |
|-------|---------|---------|
| CPython | 3.12 (required by `packaging/build.sh`) | Interpreter frozen into the binary |
| PyInstaller | 6.22.3 (hash-pinned) | Onefile freeze |
| `packaging/requirements-freeze.txt` | universal, `--require-hashes` | The only source of Python packages for the frozen binary; excludes `httpx` |

## Build Tools

| Tool | Purpose |
|------|---------|
| cargo | Rust build + test |
| pip / hatch | Python package management |
| uvicorn | Bridge server |
| pytest | Python tests |
| PyInstaller | Frozen `forgeimages-bridge` sidecar (§12) |
| GitHub Actions | `.github/workflows/freeze.yml`: engine tests, freeze, qualification on ubuntu-22.04, macos-latest, windows-latest |

## Feature Flags

| Flag | Purpose |
|------|---------|
| `test-hooks` | Counts `validate_asset()` calls so `invariant_compile_calls_validate` can prove compile always validates |

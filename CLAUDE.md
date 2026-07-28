# ForgeImages — Claude Code Context

## Project Overview

**ForgeImages** is a template-driven image asset pipeline for the Forge Ecosystem. It provides deterministic, auditable image asset generation with strict validation enforcement.

**Repository:** `ForgeImages`
**Languages:** Rust 2024 (core engine + CLI), Python 3.10+ (agent bridge + skill)

---

## Canonical Rules (NON-NEGOTIABLE)

### The Six Laws

1. **SVG Is Truth** — Vector masters are canonical; raster exports derive from them.
2. **Templates Are Contracts** — Old templates work forever. No silent behavior changes.
3. **Validation Is Protective** — Catches errors before propagation.
4. **Deterministic Output** — Same inputs = same outputs. Always.
5. **Manifests Enable Reproduction** — SHA-256 hashes link inputs to outputs.
6. **Agents Suggest, Engine Enforces** — All validation/compilation through templates. No bypasses.

### Enforcement Invariants

- `compile_asset()` ALWAYS calls `validate_asset()` — no code path bypasses this
- HTTP 422 = validation failure — agents cannot proceed past 422
- CLI exit code 2 = validation failure — bridge interprets as 422
- Audit log is append-only — never modify, truncate, or delete
- No file paths cross the trust boundary — all data is base64

---

## Module Map

```
ForgeImages/
├── forgeimages-core/           # Rust core engine
│   ├── src/
│   │   ├── lib.rs              # Library root, Six Laws, public API
│   │   ├── templates.rs        # Template contracts, registry, asset classes
│   │   ├── validation.rs       # 3 rules, validator, failure mode
│   │   ├── hashing.rs          # SHA-256, canonical JSON, job_hash
│   │   ├── print.rs            # PrintAuthority enum, print specs
│   │   ├── pipeline.rs         # CompilationPipeline (compile → validate → export)
│   │   ├── source_master.rs    # source_data ingestion: decode, admissibility, render
│   │   ├── pdf.rs              # Deterministic raster→PDF/X-1a:2001 writer
│   │   └── bin/forgeimages_cli.rs  # CLI binary
│   ├── templates/              # Template JSONs (pwa-icon, book-cover-kdp, panel-*)
│   └── tests/
│       ├── invariants.rs       # 6 contract invariant tests
│       └── source_master.rs    # master ingestion + raster→PDF/X-1a tests
│
└── forgeagents-forgeimages/    # Python agent integration
    ├── bridge/                 # FastAPI HTTP gateway
    │   ├── forgeimages_bridge.py   # 5 endpoints
    │   ├── models.py               # Pydantic v2 models
    │   ├── settings.py             # FORGEIMAGES_ env config
    │   └── audit.py                # Append-only JSONL logging
    ├── skill/
    │   └── forgeimages_skill.py    # Agent skill (async httpx)
    └── tests/
        └── test_agent_boundary.py  # 20+ boundary tests
```

---

## Coding Standards

### Rust 2024 Edition (MANDATORY)

```toml
[package]
edition = "2024"
```

- All error types use `thiserror`
- All serialization uses `serde` with `#[derive(Serialize, Deserialize)]`
- All hashing uses `sha2` crate (SHA-256)
- Semver via the `semver` crate
- `clap` derive macros for CLI

### Python Standards

- Python 3.10+
- Type hints everywhere
- Pydantic v2 for all models
- `async/await` for I/O (httpx, FastAPI)
- Validated inputs at the Pydantic layer before CLI invocation

### Agent Boundaries (Enforced)

| Agents CAN | Agents CANNOT |
|------------|---------------|
| Generate candidates | Skip validation |
| Select candidates | Override templates |
| Request compilation | Write files directly |
| List templates | Change failure mode |

---

## Key Patterns

### Validation Rule/Policy Separation

Rules produce violations. Failure mode applies policy. These are separate:
1. Rules generate `ValidationViolation` structs
2. Validator collects violations, then applies failure mode (Block/Warn/Log)

### Template Versioning

Templates use semver. Engine checks `engineMinVersion` against `ENGINE_VERSION`.

### Canonical JSON Hashing

All JSON canonicalized (sorted keys, no whitespace) before hashing. This ensures deterministic SHA-256 across platforms.

### Trust Boundary Data Flow

```
Agent → Skill (httpx) → Bridge (FastAPI) → CLI (subprocess) → Core (Rust)
                                  ↓
                         Audit Log (JSONL)
```

---

## Commands Reference

```bash
# Build Rust core
cd forgeimages-core && cargo build --release

# Run all Rust tests
cd forgeimages-core && cargo test

# Run invariant tests only
cd forgeimages-core && cargo test --test invariants

# Start bridge service
cd forgeagents-forgeimages && pip install -e . && uvicorn bridge.forgeimages_bridge:app --host 127.0.0.1 --port 8100

# Run Python tests
cd forgeagents-forgeimages && pytest tests/ -v

# CLI usage
forgeimages-cli templates --templates-dir ./templates
forgeimages-cli validate --template pwa-icon --payload '{"width":512,"height":512,"color_count":8}' --templates-dir ./templates
forgeimages-cli compile --template pwa-icon --payload '...' --templates-dir ./templates
```

---

## What NOT to Do

- **No validation bypass** — Never add a code path that skips `validate_asset()` before compilation
- **No file path exposure** — Agents receive base64, never file paths
- **No audit log mutation** — Append-only; never modify or truncate
- **No template mutation** — Bump version, never modify in place
- **No exit code changes** — Exit 2 = validation failure; bridge depends on this
- **No direct engine access** — Agents must go through the skill → bridge → CLI chain

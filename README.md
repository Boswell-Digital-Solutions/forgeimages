# bds · ForgeImages

> **System identity — bds family (Boswell Digital Solutions business system, local-systems tier).**
> Template-driven image asset pipeline for the Forge ecosystem backend; a Rust core + bridge tooling repo in `ecosystem/local-systems`.
> **Purpose:** enforces deterministic, auditable image asset validation and compilation through template-defined rules, keeping agent suggestion separate from system enforcement.

## Documentation Contract

- **Repo type:** Rust core + bridge tooling repo
- **Authority boundary:** Deterministic image validation and compilation contracts; not a resident ecosystem service and not the durable truth store
- **Deep reference:** `doc/system/_index.md`, `doc/fiSYSTEM.md`, `../docs/canonical/ecosystem_canonical.md`
- **README role:** Tooling overview and developer entrypoint
- **Truth note:** Status and language lines in this README are snapshot facts unless explicitly marked as canonical doctrine or target values

**Template-Driven Image Asset Pipeline for the Forge Ecosystem**

ForgeImages is a Rust-based image compilation system that enforces strict validation rules through templates. It provides deterministic, auditable image asset generation with a clear separation between agent suggestions and system enforcement.

**Status:** Implemented (v1.0.0)
**Language:** Rust 2024 (core engine + CLI), Python 3.10+ (agent bridge + skill)

---

## Core Principle

> **Agents suggest, ForgeImages enforces.**

AI agents can generate and select image candidates, but all validation and compilation must pass through ForgeImages' template-defined rules. No bypasses allowed.

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  ForgeAgents    │────▶│  Bridge Service  │────▶│  ForgeImages    │
│  (Python)       │     │  (FastAPI)       │     │  Core (Rust)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                        │                        │
   Skill Call             Audit Log              Validation
   (httpx)               HTTP 422               Enforced
```

### Integration with Forge Ecosystem

| Integration | Description |
|-------------|-------------|
| **VibeForge** | Primary consumer - prompt-to-image workflows (planned) |
| **ForgeAgents** | Agent orchestration via skill wrapper |
| **AuthorForge** | Future - text composition, print PDF, CMYK |

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Template Contracts** | JSON-defined validation rules per asset type |
| **PrintAuthority Enum** | Clear permission levels (System/Template/User), no conditional sprawl |
| **SHA-256 Manifests** | Cryptographic hashing for legal defensibility and reproducibility |
| **Deterministic Builds** | Same inputs always produce same job_hash |
| **Rule/Policy Separation** | Validation rules produce violations, failure mode applies policy |
| **Quantization Buckets** | Template-configurable tolerances (e.g. aspect ratio within 0.01) |

---

## Agent Boundaries (Enforced)

| Agents CAN | Agents CANNOT |
|------------|---------------|
| Generate candidates | Skip validation |
| Select candidates | Override templates |
| Request compilation | Write files directly |
| List templates | Change failure mode |

---

## Project Structure

```
ForgeImages/
├── README.md                          # This file
├── files/                             # Design documentation
│   ├── README.md                      # ForgeAgents integration guide
│   ├── CONTEXT.md                     # Trust boundary architecture
│   ├── step1-rust-core.md             # Rust core design docs
│   ├── step2-rust-cli.md              # CLI design docs
│   ├── step3-python-bridge.md         # Bridge service design docs
│   ├── step4-python-skill.md          # Skill wrapper design docs
│   ├── step5-tests.md                 # Test strategy docs
│   └── VSCODE_CLAUDE_PROMPT.md        # Implementation prompt
├── forgeimages-core/                  # Rust core engine
│   ├── Cargo.toml                     # Package manifest (v1.0.0, edition 2024)
│   ├── src/
│   │   ├── lib.rs                     # Library root (Six Laws, public API)
│   │   ├── templates.rs               # Template contracts (TemplateRegistry, AssetClass)
│   │   ├── validation.rs              # Rule/policy separation (3 rules)
│   │   ├── hashing.rs                 # SHA-256 manifests (canonical JSON, job_hash)
│   │   ├── print.rs                   # PrintAuthority enum (System/Template/User)
│   │   ├── pipeline.rs               # CompilationPipeline (compile ALWAYS validates)
│   │   └── bin/
│   │       └── forgeimages_cli.rs     # CLI binary (templates, validate, compile)
│   ├── templates/
│   │   └── pwa-icon.json              # PWA icon template (1:1, 512px min, 6 PNG exports)
│   └── tests/
│       └── invariants.rs              # Contract invariant tests (6 tests)
└── forgeagents-forgeimages/           # Python agent integration
    ├── pyproject.toml                 # Package manifest (FastAPI, Pydantic v2)
    ├── bridge/                        # FastAPI bridge service
    │   ├── forgeimages_bridge.py      # HTTP endpoints (health, templates, validate, compile)
    │   ├── models.py                  # Pydantic models (AssetInput, CompileRequest, etc.)
    │   ├── settings.py                # Configuration (cli_path, templates_dir, audit_log)
    │   └── audit.py                   # Append-only JSONL audit logging
    ├── skill/                         # ForgeAgents skill wrapper
    │   └── forgeimages_skill.py       # ForgeImagesSkill class (async httpx client)
    └── tests/
        └── test_agent_boundary.py     # Agent boundary enforcement tests (20+ tests)
```

---

## Implementation Status

- [x] Core Rust library (`forgeimages-core` v1.0.0)
- [x] Template system (`templates.rs` + `pwa-icon.json`)
- [x] Validation pipeline (`validation.rs` — AspectRatio, Resolution, ColorCount rules)
- [x] SHA-256 manifest generation (`hashing.rs` — canonical JSON, job_hash, manifest_hash)
- [x] PrintAuthority enum (`print.rs` — System/Template/User with DPI/CMYK support)
- [x] Compilation pipeline (`pipeline.rs` — compile always validates, no bypass)
- [x] CLI binary (`forgeimages-cli` — templates, validate, compile subcommands)
- [x] ForgeAgents bridge service (`forgeagents-forgeimages/bridge/`)
- [x] ForgeAgents skill wrapper (`forgeagents-forgeimages/skill/`)
- [x] Audit logging (append-only JSONL with job_hash)
- [x] Invariant tests (Rust: 6 contract tests, Python: 20+ boundary tests)
- [ ] Tauri integration for VibeForge
- [ ] MCP tool definitions

---

## Quick Start

```bash
# Build the Rust core library and CLI
cd forgeimages-core
cargo build --release

# Run invariant tests
cargo test
cargo test --test invariants

# Start the bridge service (for agent integration)
cd ../forgeagents-forgeimages
pip install -e .
uvicorn bridge.forgeimages_bridge:app --host 127.0.0.1 --port 8100

# Run agent boundary tests
pytest tests/ -v
```

### CLI Usage

```bash
# List available templates
forgeimages-cli templates --templates-dir ./templates

# Validate an asset against a template (exit code 2 = validation failure)
forgeimages-cli validate --template-id pwa-icon --templates-dir ./templates \
  --input '{"width":512,"height":512,"color_count":8}'

# Compile an asset (always validates first, exit code 2 = validation failure)
forgeimages-cli compile --template-id pwa-icon --templates-dir ./templates \
  --input '{"width":512,"height":512,"color_count":8}'
```

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Core Engine | Rust 2024 edition |
| Serialization | serde, serde_json |
| Hashing | sha2 (SHA-256) |
| Version Handling | semver |
| Error Handling | thiserror |
| CLI | clap 4.0 |
| IDs / Timestamps | uuid, chrono |
| Agent Bridge | FastAPI (Python) |
| Bridge Models | Pydantic v2 |
| Bridge HTTP Client | httpx (async) |
| Audit | Append-only JSONL |

---

## Bridge HTTP Endpoints

| Method | Endpoint | Purpose | Error Semantics |
|--------|----------|---------|-----------------|
| GET | `/health` | Health check | 200 |
| GET | `/templates` | List available templates | 200 |
| GET | `/template/{id}` | Get template details | 200 / 404 |
| POST | `/validate/{id}` | Validate asset against template | 200 / 422 |
| POST | `/compile/{id}` | Compile asset (validates first) | 200 / 422 |

HTTP 422 is returned when validation fails. The response body contains structured violations with remediation hints.

---

## Codebase Metrics

| Metric | Count |
|--------|-------|
| Rust source files | 7 (lib + 5 modules + CLI) |
| Python source files | 6 (bridge: 4, skill: 1, init: 1) |
| Test files | 2 (Rust invariants + Python boundaries) |
| Rust LOC | ~1,100 |
| Python LOC | ~800 |
| Test LOC | ~500 |
| Template files | 1 (pwa-icon.json) |
| Validation rules | 3 (AspectRatio, Resolution, ColorCount) |
| CLI subcommands | 3 (templates, validate, compile) |

---

**Maintained by:** Boswell Digital Solutions LLC
**Part of:** Forge Ecosystem v5.3

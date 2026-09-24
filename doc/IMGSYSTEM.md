# ForgeImages - Compiled System Reference

**Designation:** IMG
**Document role:** Canonical compiled technical reference for the ForgeImages asset pipeline
**Source:** `doc/system/`
**Build command:** `bash doc/system/BUILD.sh`
**Document version:** 2.0 (2026-06-22) - canonical compliance migration
**Protocol:** BDS Documentation Protocol v2.0; BDS Repo Documentation System Canonical Compliance Standard

> **Generated artifact warning:** `doc/IMGSYSTEM.md` is assembled output. Edit
> the source modules under `doc/system/` and rebuild. Hand edits to the
> compiled artifact are overwritten by the next build.

Assembly contract:

- Command: `bash doc/system/BUILD.sh`
- Validation: `bash doc/system/validate_snapshots.sh` runs during assembly
- Primary output: `doc/IMGSYSTEM.md`

This `doc/system/` tree is the canonical source of truth for ForgeImages. It
uses explicit **truth classes**: canonical facts define the repo role, authority
boundaries, runtime behavior, service contracts, and verification doctrine;
snapshot facts are dated, audit-derived counts and current implementation
inventory that may drift between audits.

| Part | File | Contents |
| --- | --- | --- |
| §1 | `00_overview/01-overview-philosophy.md` | §1 — Overview & Philosophy |
| §2 | `00_overview/02-architecture.md` | §2 — Architecture |
| §3 | `00_overview/04-project-structure.md` | §4 — Project Structure |
| §4 | `10_service-contract/06-api-layer.md` | §6 — API Layer |
| §5 | `20_runtime/07-backend-internals.md` | §7 — Backend Internals |
| §6 | `20_runtime/09-error-handling.md` | §9 — Error Handling |
| §7 | `30_dependencies/03-tech-stack.md` | §3 — Tech Stack |
| §8 | `30_dependencies/08-ecosystem-integration.md` | §8 — Ecosystem Integration |
| §9 | `40_governance/10-scope.md` | Scope |
| §10 | `40_governance/30-governance.md` | Governance |
| §11 | `40_governance/40-change-control.md` | Change Control |
| §12 | `50_operations/05-config-env.md` | §5 — Configuration & Environment |
| §13 | `50_operations/10-testing.md` | §10 — Testing |
| §14 | `50_operations/11-handover.md` | §11 — Handover |
| §15 | `99_appendices/20-structure.md` | §4 — Project Structure |
| §16 | `99_appendices/90-appendices.md` | Appendices |
| §17 | `99_appendices/91-bootstrap-overview.md` | §1 — Overview & Philosophy |
| §18 | `99_appendices/92-bootstrap-architecture.md` | §2 — Architecture |

## Quick Assembly

```bash
bash doc/system/BUILD.sh
```

---

# §1 — Overview & Philosophy

> **System identity — bds family (Boswell Digital Solutions business system, local-systems tier).** ForgeImages is the template-driven image asset pipeline for the Forge ecosystem backend, implemented as a Rust core + bridge tooling repo in `ecosystem/local-systems`.

## Service Identity

**ForgeImages** is the template-driven image asset pipeline for the Forge Ecosystem. It provides deterministic, auditable image asset generation with strict validation enforcement and a clear separation between agent suggestions and system enforcement.

- **Version:** v1.0.0
- **Status:** Implemented (core engine + bridge + skill)
- **Languages:** Rust 2024 (core engine + CLI), Python 3.10+ (agent bridge + skill)
- **LOC:** ~2,400 (Rust ~1,100, Python ~800, Tests ~500)

## The Six Laws (Non-Negotiable)

These are the canonical invariants. Every code path, every test, every design decision traces back to one of these laws.

1. **SVG Is Truth** — Vector masters are the canonical source; all raster exports derive from them.
2. **Templates Are Contracts** — Old templates work forever. New engines never silently change behavior. Version mismatch = clear error.
3. **Validation Is Protective** — Validation exists to catch errors before they propagate, not to punish users.
4. **Deterministic Output** — Same inputs always produce the same outputs. Manifest hashes are stable and reproducible.
5. **Manifests Enable Reproduction** — SHA-256 hashes link inputs to outputs for legal defensibility and auditability.
6. **Agents Suggest, Engine Enforces** — AI agents can generate and select candidates, but all validation and compilation must pass through ForgeImages' template-defined rules. No bypasses allowed.

## Core Principle

> **Agents suggest, ForgeImages enforces.**

This is not a guideline. It is an architectural invariant enforced at three levels:

1. **Rust type system** — `compile_asset()` always calls `validate_asset()` internally
2. **HTTP status codes** — Bridge returns 422 on validation failure; agents cannot proceed
3. **CLI exit codes** — Exit code 2 = validation failure; bridge interprets this as 422

## Ecosystem Role

```
┌──────────────────────────────────────────────────────────────┐
│                      Forge Ecosystem                          │
│                                                              │
│   VibeForge     ForgeAgents     AuthorForge                 │
│   (consumer)    (orchestration)  (future)                    │
│       │              │              │                        │
│       └──────────────┴──────────────┘                        │
│                      │                                       │
│          ┌───────────▼────────────┐                          │
│          │   ForgeImages Bridge   │  ← HTTP gateway          │
│          │   (Python / FastAPI)   │                          │
│          └───────────┬────────────┘                          │
│                      │ subprocess                            │
│          ┌───────────▼────────────┐                          │
│          │   ForgeImages Core     │  ← Validation + compile  │
│          │   (Rust 2024)          │                          │
│          └────────────────────────┘                          │
└──────────────────────────────────────────────────────────────┘
```

## What ForgeImages Is

- **A validation engine** — Enforces template-defined rules on image assets
- **A compilation pipeline** — Produces deterministic, hashed export bundles
- **An audit trail** — Every request is logged with job hashes linking inputs to outputs
- **A trust boundary** — Agents interact through the skill/bridge layer; they never touch the engine directly

## What ForgeImages Is Not

- **Not an image editor.** It does not provide editing tools; it validates and compiles assets.
- **Not a storage service.** Compiled assets are returned as base64; persistence is the caller's responsibility.
- **Not an AI model.** It does not generate images; agents upstream (VibeForge) handle generation.
- **Not a CDN.** It produces export bundles; distribution is handled elsewhere.

## Codebase Metrics

| Metric | Count |
|--------|-------|
| Rust source files | 7 (lib + 5 modules + CLI) |
| Python source files | 6 (bridge: 4, skill: 1, init: 1) |
| Test files | 2 (Rust invariants + Python boundaries) |
| Template files | 1 (pwa-icon.json) |
| Validation rules | 3 (AspectRatio, Resolution, ColorCount) |
| CLI subcommands | 3 (templates, validate, compile) |
| Bridge endpoints | 5 (health, templates, template/:id, validate/:id, compile/:id) |
| Test methods | 26+ (Rust: 6 invariant, Python: 20+ boundary) |

---

# §2 — Architecture

## Three-Tier Trust Boundary

ForgeImages enforces a strict three-tier architecture where each layer has defined responsibilities and no layer can bypass the one below it.

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  ForgeAgents    │────▶│  Bridge Service  │────▶│  ForgeImages    │
│  (Python)       │     │  (FastAPI)       │     │  Core (Rust)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                        │                        │
   Skill Call             Audit Log              Validation
   (httpx)               HTTP 422               Enforced
```

### Layer 1: Agent Skill (Python — `skill/`)

The agent-facing interface. Provides async methods for template listing, validation, and compilation. Communicates exclusively via HTTP to the bridge service.

**Agents CAN:**
- Generate image candidates
- Select candidates
- Request compilation
- List available templates

**Agents CANNOT:**
- Skip validation
- Override templates
- Write files directly
- Change failure mode

### Layer 2: Bridge Service (Python — `bridge/`)

The HTTP gateway between agents and the Rust engine. Handles request validation (Pydantic v2), audit logging (append-only JSONL), and subprocess management (CLI invocation).

**Bridge responsibilities:**
- Pydantic input validation (dimensions 1-10000, template ID format)
- Versioned NeuroForge validation request/result contracts with fail-closed schema and enum handling
- Audit logging with job hash linkage
- CLI subprocess execution with 30-second timeout
- Structured error responses (422 with violations + remediation)
- Request size limiting

The cloud-image fulfillment boundary is provider-free. NeuroForge owns cloud
generation and the fulfillment saga; ForgeImages owns deterministic validation
and compilation. ForgeImages does not select or invoke generation providers.
Slice 01 defines the transport models. Slice 02 adds an offline metadata
validator, governed profiles, and content-addressed manifests without exposing
a public route or claiming artifact-byte inspection.

### Layer 3: Core Engine (Rust — `forgeimages-core/`)

The validation and compilation engine. Template contracts, validation rules, SHA-256 manifest generation, and export rendering. This is the enforcement layer.

**Engine guarantees:**
- `compile_asset()` ALWAYS calls `validate_asset()` — no code path bypasses this
- Template version compatibility is checked via semver
- All outputs include deterministic manifest hashes
- Canonical JSON ensures hash stability across platforms

## Data Flow: Compile Request

```
Agent                   Bridge                    Engine
  │                       │                         │
  │──POST /compile/X────▶│                         │
  │                       │──call_cli(compile)────▶│
  │                       │                         │──validate_asset()
  │                       │                         │──check_engine_version()
  │                       │                         │──generate_exports()
  │                       │                         │──compute_job_hash()
  │                       │◀──JSON + exit code──────│
  │                       │──audit_log.log()        │
  │◀──200 CompiledAsset──│                         │
  │   or 422 violations   │                         │
```

## Data Flow: Validation Failure

```
Agent                   Bridge                    Engine
  │                       │                         │
  │──POST /validate/X───▶│                         │
  │                       │──call_cli(validate)───▶│
  │                       │                         │──run 3 rules
  │                       │                         │──apply failure_mode
  │                       │◀──exit code 2 + JSON───│
  │                       │──audit_log.log()        │
  │◀──422 + violations───│                         │
  │                       │                         │
  │  (agent CANNOT        │                         │
  │   proceed past 422)   │                         │
```

## PrintAuthority Model

The PrintAuthority enum determines the source of physical output specifications:

```
PrintAuthority::System    → Default (300 DPI, RGB, 0.125" bleed)
PrintAuthority::Template  → Template-defined specs
PrintAuthority::User      → User-provided (validated: 72-1200 DPI, 0-1" bleed)
```

This eliminates conditional sprawl — the enum determines behavior, not nested if/else chains.

## Template Contract Model

Templates are JSON files that define:
- Asset class (Icon, Cover, Banner, Logo)
- Aspect ratio with quantization tolerance
- Minimum resolution constraints
- Color count limits
- Export specifications (format, size, required flag)
- Failure mode (Block, Warn, Log)
- Engine version compatibility

Templates are versioned via semver. The engine checks `engineMinVersion` against `ENGINE_VERSION` before processing.

## Key Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| Rust core, Python bridge | Rust for determinism + safety; Python for agent ecosystem integration |
| CLI subprocess (not FFI) | Clean process boundary; exit codes are the enforcement mechanism |
| HTTP 422 for validation | Standard HTTP semantics; agents must handle 422 to proceed |
| Append-only audit log | Legal defensibility; no mutation of historical records |
| Base64 export data | No file paths cross the trust boundary; data is self-contained |
| Canonical JSON hashing | Platform-independent determinism for manifest verification |
| Mirrored v1 fulfillment contracts | NeuroForge and ForgeImages exchange strict JSON without sharing runtime dependencies |
| Offline candidate validator | Metadata checks are deterministic and testable before durable artifact access exists |
| Self-verifying manifest | Canonical JSON content is bound to a SHA-256 digest and rejects tampering |

---

# §4 — Project Structure

## Directory Tree

```
ForgeImages/
├── README.md                          # Project overview and quick start
├── CLAUDE.md                          # AI assistant coding standards
├── .gitignore                         # Build artifacts, venvs, audit logs
│
├── doc/                               # Forge Documentation Protocol docs
│   ├── system/                        # Modular system documentation parts
│   │   ├── _index.md                  # Master table of contents
│   │   ├── 01-overview-philosophy.md  # §1: Six Laws, ecosystem role
│   │   ├── 02-architecture.md         # §2: Trust boundary, data flow
│   │   ├── 03-tech-stack.md           # §3: Dependencies and versions
│   │   ├── 04-project-structure.md    # §4: This file
│   │   ├── 05-config-env.md           # §5: Environment and CLI flags
│   │   ├── 06-api-layer.md            # §6: Bridge endpoints, CLI commands
│   │   ├── 07-backend-internals.md    # §7: Template, validation, hashing, pipeline
│   │   ├── 08-ecosystem-integration.md # §8: ForgeAgents, VibeForge, AuthorForge
│   │   ├── 09-error-handling.md       # §9: 422 contract, exit codes, violations
│   │   ├── 10-testing.md             # §10: Invariant + boundary tests
│   │   ├── 11-handover.md            # §11: Constraints, deployment, future
│   │   └── BUILD.sh                   # Assembles parts into context-bundle.md
│   └── SYSTEM.md                      # Generated: full assembled reference
│
├── scripts/
│   └── context-bundle.sh             # AI session context generator (presets)
│
├── files/                             # Design documentation (pre-implementation)
│   ├── README.md                      # ForgeAgents integration guide
│   ├── CONTEXT.md                     # Trust boundary architecture
│   ├── step1-rust-core.md             # Rust core design spec
│   ├── step2-rust-cli.md              # CLI design spec
│   ├── step3-python-bridge.md         # Bridge service design spec
│   ├── step4-python-skill.md          # Skill wrapper design spec
│   ├── step5-tests.md                 # Test strategy spec
│   └── VSCODE_CLAUDE_PROMPT.md        # Implementation prompt
│
├── forgeimages-core/                  # Rust core engine
│   ├── Cargo.toml                     # Package: forgeimages-core v1.0.0, edition 2024
│   ├── src/
│   │   ├── lib.rs                     # Library root — Six Laws, public API exports
│   │   ├── templates.rs               # Template contracts (TemplateRegistry, AssetClass, ExportSpec)
│   │   ├── validation.rs              # Rule/policy separation (3 rules, Validator, FailureMode)
│   │   ├── hashing.rs                 # SHA-256 manifests (canonical JSON, job_hash, manifest_hash)
│   │   ├── print.rs                   # PrintAuthority enum (System/Template/User, DPI/CMYK)
│   │   ├── pipeline.rs               # CompilationPipeline (compile ALWAYS validates, exports)
│   │   └── bin/
│   │       └── forgeimages_cli.rs     # CLI binary (templates, validate, compile subcommands)
│   ├── templates/
│   │   └── pwa-icon.json              # PWA icon template (1:1, 512px min, 6 PNG + 1 SVG)
│   └── tests/
│       └── invariants.rs              # Contract invariant tests (6 tests)
│
└── forgeagents-forgeimages/           # Python agent integration
    ├── pyproject.toml                 # Package: forgeagents-forgeimages v1.0.0, Python >=3.10
    ├── bridge/                        # FastAPI bridge service
    │   ├── __init__.py                # Package init
    │   ├── cloud_fulfillment_contracts.py # Versioned NeuroForge validation contracts
    │   ├── cloud_fulfillment_manifest.py # Deterministic validation manifest
    │   ├── cloud_fulfillment_profiles.py # Immutable technical profiles
    │   ├── cloud_fulfillment_validation.py # Offline candidate validator
    │   ├── forgeimages_bridge.py      # HTTP endpoints (health, templates, validate, compile)
    │   ├── models.py                  # Pydantic v2 models (AssetInput, CompileRequest, etc.)
    │   ├── settings.py                # Configuration (FORGEIMAGES_ env prefix)
    │   └── audit.py                   # Append-only JSONL audit logging
    ├── skill/                         # ForgeAgents skill wrapper
    │   ├── __init__.py                # Package init
    │   └── forgeimages_skill.py       # ForgeImagesSkill class (async httpx client)
    └── tests/
        ├── test_agent_boundary.py     # Agent boundary enforcement tests
        ├── test_forgeimages_asset_manifest.py
        ├── test_forgeimages_asset_validator.py
        ├── test_forgeimages_validation_contracts.py
        └── test_forgeimages_rejection_report_contract.py
```

## Key Module Responsibilities

### Rust Modules

| Module | LOC | Responsibility |
|--------|-----|----------------|
| `lib.rs` | 25 | Six Laws docstring, public API re-exports, version constants |
| `templates.rs` | 176 | Template, AssetClass, ValidationConfig, ExportSpec, TemplateRegistry |
| `validation.rs` | 224 | 3 rules (AspectRatio, Resolution, ColorCount), Validator, FailureMode |
| `hashing.rs` | 102 | SHA-256, canonical JSON (sorted keys), job_hash, manifest_hash |
| `print.rs` | 81 | PrintAuthority enum, PrintSpec, ColorSpace, DPI/bleed validation |
| `pipeline.rs` | 272 | CompilationPipeline, CompileRequest, CompiledAsset, ExportedFile |
| `forgeimages_cli.rs` | 149 | Clap CLI: templates, validate (exit 2), compile (exit 2) |

### Python Modules

| Module | LOC | Responsibility |
|--------|-----|----------------|
| `models.py` | 93 | Pydantic v2 models mirroring Rust types |
| `cloud_fulfillment_contracts.py` | — | Strict v1 validation request, result, rejection, and compiled-asset records |
| `cloud_fulfillment_manifest.py` | — | Canonical manifest construction and digest verification |
| `cloud_fulfillment_profiles.py` | — | Read-only profile registry for technical production thresholds |
| `cloud_fulfillment_validation.py` | — | Provider-free MIME, resolution, ratio, safe-zone, and crop metadata checks |
| `settings.py` | 33 | Environment-based config (FORGEIMAGES_ prefix) |
| `audit.py` | 105 | Append-only JSONL audit log with job hash linkage |
| `forgeimages_bridge.py` | 272 | FastAPI app with 5 endpoints, CLI subprocess calls |
| `forgeimages_skill.py` | 378 | ForgeImagesSkill class, async httpx, error handling |

---

# §6 — API Layer

## Bridge HTTP Endpoints

The bridge service runs on `http://127.0.0.1:8100` (configurable via uvicorn).

### Endpoint Reference

| Method | Endpoint | Purpose | Success | Failure |
|--------|----------|---------|---------|---------|
| GET | `/health` | Health check | 200 | — |
| GET | `/templates` | List all templates | 200 `list[TemplateInfo]` | — |
| GET | `/template/{id}` | Get template details | 200 `dict` | 404 |
| POST | `/validate/{id}` | Validate asset against template | 200 `ValidationResult` | 422 |
| POST | `/compile/{id}` | Compile asset (validates first) | 200 `CompileResponse` | 422 |

### Request/Response Models

**POST /validate/{template_id}**
```json
// Request body (AssetInput)
{
  "width": 512,        // 1-10000
  "height": 512,       // 1-10000
  "color_count": 8,    // optional, 1-256
  "format": "png"      // optional
}

// Success response (ValidationResult)
{
  "valid": true,
  "violations": [],
  "template_id": "pwa-icon",
  "template_version": "1.0.0"
}

// Failure response (HTTP 422)
{
  "valid": false,
  "violations": [
    {
      "rule": "aspect_ratio",
      "severity": "error",
      "message": "Aspect ratio 2.00 exceeds tolerance ...",
      "expected": "1.00",
      "actual": "2.00",
      "remediation": ["Resize to 1:1 aspect ratio"]
    }
  ],
  "template_id": "pwa-icon",
  "template_version": "1.0.0"
}
```

**POST /compile/{template_id}**
```json
// Request body (CompileRequest)
{
  "template_id": "pwa-icon",
  "asset_input": { "width": 512, "height": 512, "color_count": 8 },
  "source_data": "base64...",   // optional
  "seed": 42,                   // optional
  "prompt": "..."               // optional, max 2000 chars
}

// Success response (CompileResponse)
{
  "success": true,
  "asset": {
    "id": "uuid",
    "template_id": "pwa-icon",
    "template_version": "1.0.0",
    "engine_version": "1.0.0",
    "created_at": "2026-01-15T12:00:00Z",
    "manifest_hash": "sha256:...",
    "job_hash": "sha256:...",
    "validation": { "valid": true, "violations": [] },
    "exports": [
      {
        "id": "master",
        "filename": "master.svg",
        "format": "svg",
        "size": [1024, 1024],
        "data_base64": "...",
        "hash": "sha256:..."
      }
    ]
  }
}
```

### `source_data` — supplying a master

`source_data` carries a base64 master asset. It is optional; when present it is
**authoritative**, and the governing rule is:

> A supplied master is never silently ignored. If it cannot be decoded, is not
> admissible for the template, or cannot be converted to a required export, the
> compile **fails**. It never falls back to the placeholder export.

That rule exists because the opposite was previously true: `source_data` was
accepted, transported and canonicalized into `job_hash`, but read by no code — so
a caller who supplied a master received a placeholder asset accompanied by a hash
asserting the master had been compiled.

**Accepted masters** — SVG markup (tolerating a BOM/XML prolog), or a raster
decodable by the enabled `image` features (PNG/JPEG/TIFF). Sniffing alone is not
enough: the raster is fully decoded up front, so a truncated file carrying a
valid magic number is rejected here rather than failing later during encoding.

**Admissibility**, checked before any export is produced:

| Condition | Result |
|---|---|
| Template declares `vectorMaster: true` and the master is raster | Refused — Law 1, *SVG Is Truth* |
| `asset_input` dimensions differ from the master's real dimensions | Refused — validation ran against an asset that is not the one being compiled |

**Conversions implemented** (both deterministic, Law 4):

| Master | Export | Behaviour |
|---|---|---|
| SVG | `svg` | Pass-through |
| Raster | `png` / `jpg`, size matches | Pass-through (no re-encode, so the hash stays stable) |
| Raster | `png` / `jpg`, size differs | Lanczos3 resize + re-encode |
| Raster (opaque grayscale) | `pdf` | **PDF/X-1a:2001** via the deterministic writer (`pdf.rs`): the master is embedded at 300 DPI with `MediaBox`/`TrimBox`/`OutputIntent` and no transparency |

Everything else is **refused explicitly** rather than approximated: an SVG master
to `pdf` (no rasterizer), raster→`ico`, and — the case that matters for covers —
a **non-grayscale** raster to `pdf`. PDF/X-1a is a device grayscale/CMYK print
standard, and turning an RGB diffusion master into CMYK is a color-managed step
ForgeImages will not invent; it refuses with that reason rather than emit a
"print-ready" file built on made-up color. So `book-cover-kdp` (whose PDF/X-1a
export is `required`) now compiles from a supplied **grayscale** cover master and
refuses precisely for an RGB one — the remaining gate is a chosen RGB→CMYK output
intent, not a missing writer. See §7 for the writer's conformance boundary.

**When `source_data` is absent**, behaviour is unchanged: exports are placeholders
(an empty `<svg>`, a 1x1 PNG, or `b"placeholder"`), because export *rendering* is
still unimplemented. That predates this change and is not widened by it — but it
does mean a no-master compile of `book-cover-kdp` still returns a placeholder for
a file described as print-ready.

### Error Semantics

| HTTP Status | Meaning | When |
|-------------|---------|------|
| 200 | Success | Valid asset or successful compilation |
| 404 | Not found | Template ID does not exist |
| 422 | Validation failure | Asset violates template rules (blocking mode) |
| 503 | Service unavailable | Rust CLI binary not found |
| 504 | Timeout | CLI execution exceeded 30 seconds |

### Middleware

- **Request size limiter** — Enforces `max_request_size_mb` (default 10 MB)

### Headers

| Header | Direction | Purpose |
|--------|-----------|---------|
| `X-User-ID` | Request | Optional user identification for audit trail |
| `Content-Type` | Both | `application/json` |

## NeuroForge Cloud-Fulfillment Contracts (Slice 01)

`bridge/cloud_fulfillment_contracts.py` defines the provider-free JSON boundary
that a later route will use. No cloud-fulfillment endpoint is exposed through
Slice 02: durable manifest storage and artifact-byte access do not yet exist,
and the service must not advertise an unresolvable production result.

Top-level payloads carry `schema_version`, `correlation_id`,
`idempotency_key`, `source_service`, `target_service`, and timezone-aware
`created_at` metadata. Unknown schema versions, unknown rejection codes,
unrecognized fields, naive timestamps, or inconsistent result counts fail
Pydantic validation.

| Contract | Schema version | Direction |
|---|---|---|
| `ForgeImagesValidationRequestV1` | `forgeimages_validation_request.v1` | NeuroForge → ForgeImages |
| `ForgeImagesValidationResultV1` | `forgeimages_validation_result.v1` | ForgeImages → NeuroForge |

The request contains service-owned candidate artifact references and a
validation profile. The result contains accepted candidates, structured
rejections, replacement counts, compiled-asset summaries, and an optional
manifest URI. Provider details are neither accepted nor returned by this
contract.

Rejections use `soft_fail` or `hard_fail` severity and one of these stable
codes: `safe_zone_failed`, `aspect_ratio_invalid`, `resolution_too_low`,
`subject_cutoff`, `subject_too_close_to_edge`, `template_slot_failed`,
`text_area_blocked`, `unwanted_text_present`, `crop_not_viable`,
`composition_not_asset_ready`, `brand_layout_failed`, `file_decode_failed`,
`unsupported_format`, `transparency_required_missing`, or
`unknown_validation_failure`.

### Slice 02 offline validation service

`DeterministicCloudAssetValidator.validate()` accepts a parsed
`ForgeImagesValidationRequestV1` and returns a
`CloudAssetValidationOutput` containing the versioned result and an inline,
self-verifying `ForgeImagesAssetManifestV1`.

The initial checks execute in a stable order: supported MIME type, minimum
resolution, expected aspect ratio, controlled force-reject metadata, optional
safe-zone signal, then optional crop-viability signal. One primary rejection is
reported per artifact. `replacement_count` equals the number of `hard_fail`
rejections; soft failures remain reported but do not request replacement.

Production validator instances reject test metadata. Tests must explicitly
construct the service with `allow_test_metadata=True`. The default service
accepts PNG, JPEG, and TIFF because those are the raster formats currently
decoded by the Rust core; WebP therefore fails closed as `unsupported_format`.

The manifest records validation/job lineage, sorted accepted and rejected
artifact identifiers, template/profile identifiers, compiled asset IDs, export
variants, and a SHA-256 digest of canonical compact JSON. Slice 02 leaves
compiled asset IDs and export variants empty and returns no `manifest_uri`
because compilation and durable manifest persistence are not implemented by
this slice.

## CLI Subcommands

The Rust CLI is invoked by the bridge as a subprocess. It is also usable directly.

### `templates` — List Templates

```bash
forgeimages-cli templates --templates-dir ./templates
```

Output: JSON array of template summaries.

### `validate` — Validate Asset

```bash
forgeimages-cli validate \
  --template pwa-icon \
  --payload '{"width":512,"height":512,"color_count":8}' \
  --templates-dir ./templates
```

Output: JSON ValidationResult. Exit code 0 = valid, exit code 2 = invalid.

### `compile` — Compile Asset

```bash
forgeimages-cli compile \
  --template pwa-icon \
  --payload '{"template_id":"pwa-icon","asset_input":{"width":512,"height":512,"color_count":8}}' \
  --templates-dir ./templates
```

Output: JSON CompiledAsset. Exit code 0 = success, exit code 2 = validation/compilation failure.

### CLI Exit Code Semantics

| Code | Meaning | Bridge Interpretation |
|------|---------|----------------------|
| 0 | Success | HTTP 200 |
| 1 | System error | HTTP 500 |
| 2 | Validation failure | HTTP 422 |

---

# §7 — Backend Internals

## Template System (`templates.rs`)

### Core Types

**Template** — The contract definition:
- `id: TemplateId` — Unique identifier (e.g., "pwa-icon")
- `name: String` — Human-readable name
- `template_version: Version` — Semver version
- `engine_min_version: Version` — Minimum compatible engine
- `asset_class: AssetClass` — Icon, Cover, Banner, or Logo
- `aspect_ratio: (u32, u32)` — Expected ratio
- `canonical_size: (u32, u32)` — Ideal dimensions
- `vector_master: bool` — Whether SVG master is required
- `validation: ValidationConfig` — Rules and failure mode
- `exports: Vec<ExportSpec>` — Output specifications

**AssetClass enum** — `Icon | Cover | Banner | Logo`

**FailureMode enum** — Determines what happens when validation finds errors:
- `Block` (default) — Errors prevent compilation
- `Warn` — Errors recorded but compilation proceeds
- `Log` — Errors recorded silently

**TemplateRegistry** — HashMap-backed registry:
- `load_from_dir(path)` — Loads all `.json` files from directory
- `get(id)` — Retrieve template by ID
- `list()` — List all registered templates
- `register(template)` — Add a template to the registry

### Template Versioning

Templates use semver. The engine checks compatibility before processing:

```rust
fn check_engine_version(template: &Template) -> Result<(), PipelineError> {
    let engine = Version::parse(ENGINE_VERSION)?;
    if engine < template.engine_min_version {
        return Err(PipelineError::EngineVersionMismatch { ... });
    }
    Ok(())
}
```

## Validation Pipeline (`validation.rs`)

### Rule/Policy Separation

Validation rules produce violations. Failure mode applies policy. These are intentionally separate concerns:

1. **Rules** generate `ValidationViolation` structs with severity, message, expected/actual values, and remediation hints
2. **Validator** collects all violations from all rules, then applies the failure mode policy to determine `valid: bool`

### Three Validation Rules

**AspectRatioRule** — Compares input width:height ratio against template target within configurable tolerance.
```
expected_ratio = template.aspect_ratio.0 / template.aspect_ratio.1
actual_ratio = input.width / input.height
valid = |expected - actual| <= tolerance
```

**ResolutionRule** — Enforces minimum width and height from template config.
```
valid = input.width >= min_width && input.height >= min_height
```

**ColorCountRule** — Enforces maximum color palette. Severity is `Warning` (not Error), so it never blocks in Block mode.
```
valid = input.color_count <= max_colors
```

### Failure Mode Application

| Mode | Error violations | Warning violations | Result |
|------|------------------|--------------------|--------|
| Block | `valid = false` | Recorded, not blocking | Blocks compilation |
| Warn | Recorded | Recorded | Never blocks |
| Log | Recorded | Recorded | Never blocks |

## SHA-256 Hashing (`hashing.rs`)

### Canonical JSON

All JSON is canonicalized before hashing: keys sorted alphabetically, no whitespace, nested objects recursively sorted. This ensures identical hashes across platforms and serialization orders.

```rust
pub fn canonical_json<T: Serialize>(value: &T) -> Result<String, serde_json::Error> {
    let v = serde_json::to_value(value)?;
    let sorted = sort_value(&v);  // Recursive key sorting
    serde_json::to_string(&sorted)
}
```

### Hash Functions

**`compute_manifest_hash(value)`** — SHA-256 of canonical JSON representation. Used for content-addressable identification.

**`compute_job_hash(template_id, template_version, payload, engine_version)`** — SHA-256 of concatenated string:
```
"{template_id}:{template_version}:{canonical_payload}:{engine_version}"
```
Links a specific compilation request to its output. Used in audit trail to verify that the same inputs produce the same outputs.

## Print Authority (`print.rs`)

### PrintAuthority Enum

| Variant | DPI | Color Space | Bleed | Use Case |
|---------|-----|-------------|-------|----------|
| System | 300 | RGB | 0.125" | Default fallback |
| Template | Template-defined | Template-defined | Template-defined | Template specifies print requirements |
| User | User-provided | User-provided | User-provided | User override with validation |

### User Validation Constraints

| Property | Range | Error |
|----------|-------|-------|
| DPI | 72-1200 | Out of range |
| Bleed | 0-1 inch | Out of range |

### ColorSpace Enum

`Rgb | Cmyk | Grayscale` — Serialized as UPPERCASE strings.

## Raster→PDF/X-1a Writer (`pdf.rs`)

`write_pdf_x1a` turns print-admissible raster samples into a single-page
PDF/X-1a:2001 document. It is the render step that lets `book-cover-kdp` produce
its `required` `cover-pdf` export instead of a placeholder (see §6 for how the
master reaches it).

### Design constraints

- **Deterministic (Law 4).** The output is a pure function of `(samples,
  geometry, output intent)`. The PDF is hand-written, not produced by a library,
  precisely to keep the three usual sources of non-determinism out of the
  reproducibility path: the `CreationDate`/`ModDate` are a fixed synthetic
  constant, the `/ID` is derived from a content hash, and the image stream is
  stored **uncompressed** (no encoder version to drift under the hash).
- **Device color only.** `DeviceColor` is `Gray | Cmyk` — there is no RGB
  variant, because PDF/X-1a forbids RGB. An inadmissible master is therefore
  refused in `source_master.rs` (with a named reason) before it can reach the
  writer.
- **Geometry.** `points = pixels / dpi * 72`. The image fills the `MediaBox`
  (full bleed); the `TrimBox` is inset by the bleed. `MediaBox`, `TrimBox`,
  `BleedBox`, `OutputIntents`, `GTS_PDFXVersion` and `Trapped` are all emitted.

### Conformance boundary

The file is *structurally* PDF/X-1a:2001, and its blind-exchange conformance is
only as strong as the `OutputIntent` it is given. The default
(`OutputIntent::kdp_us_swop`) references the registered U.S. Web Coated (SWOP)
condition **by name** (spec-permitted, and carries no licensed ICC into the
repo); a deployment that needs an embedded `DestOutputProfile` — or a different
condition — supplies its own intent. The module does not claim a file passes a
specific vendor's preflight; that is a deployment-time check with a real profile.

## Compilation Pipeline (`pipeline.rs`)

### The Critical Invariant

```rust
pub fn compile_asset(&self, request: CompileRequest) -> Result<CompiledAsset, PipelineError> {
    // ALWAYS validate first — this is the Six Laws in code
    let validation = self.validate_asset(&request.template_id, &request.asset_input)?;
    if !validation.valid {
        return Err(PipelineError::ValidationFailed(validation));
    }
    // ... proceed with compilation
}
```

There is no code path that reaches export generation without first passing through validation. This is enforced by the Rust type system and tested in `invariants.rs`.

### Pipeline Steps

1. **Resolve template** — Look up template by ID from registry
2. **Check engine version** — Semver compatibility check
3. **Validate asset** — Run 3 rules, apply failure mode
4. **Generate exports** — Create one ExportedFile per ExportSpec
5. **Compute hashes** — manifest_hash + job_hash
6. **Return CompiledAsset** — Immutable result with all metadata

### ExportedFile

Each export contains:
- `id` — Matches the ExportSpec ID (e.g., "favicon-32")
- `filename` — Generated filename (e.g., "favicon-32.png")
- `format` — ExportFormat enum value
- `size` — Pixel dimensions
- `data_base64` — Base64-encoded file content
- `hash` — SHA-256 of the raw file data

## Audit Logging (`audit.py`)

Append-only JSONL format. Each entry contains:

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | ISO 8601 | When the request was processed |
| `request_id` | UUID | Unique request identifier |
| `user_id` | string? | From X-User-ID header |
| `template_id` | string | Which template was used |
| `job_hash` | string | SHA-256 linking input to output |
| `action` | string | "validate" or "compile" |
| `outcome` | string | "success", "validation_failed", or "error" |
| `violations_count` | int | Number of violations found |
| `error_message` | string? | Error details if outcome is "error" |

The audit logger computes `job_hash` using the same algorithm as the Rust engine, ensuring cross-layer linkage.

## Cloud-Fulfillment Contract Boundary

`bridge/cloud_fulfillment_contracts.py` is deliberately isolated from the Rust
compilation pipeline. It validates the v1 transport envelope and nested record
shape before later slices connect those records to deterministic validation.
The module imports only standard-library typing/date primitives and Pydantic;
it has no cloud generation client dependency.

Request service identities are locked to `neuroforge` → `forgeimages`; result
identities are locked to `forgeimages` → `neuroforge`. Exact `Literal` schema
versions and enum-backed rejection codes make peer drift fail closed. Result
model validation also requires accepted/rejected counts to match their lists
and replacement flags to match the replacement count.

### Slice 02 profiles and validation

`cloud_fulfillment_profiles.py` defines immutable AuthorForge, PressForge, and
internal-smoke profiles. The registry rejects duplicate or unknown profile IDs.
The production profiles specify supported MIME types, minimum dimensions,
aspect-ratio tolerance, and whether optional safe-zone/crop signals apply.

`cloud_fulfillment_validation.py` evaluates only contract metadata and explicit
signals. It performs no network requests, file reads, image decoding, provider
selection, or compilation. Validation IDs and result idempotency keys are
SHA-256-derived from stable request identity. Duplicate artifact or candidate
IDs and metadata for unknown artifacts fail closed.

`CandidateValidationMetadata` is a controlled placeholder/test seam. Force
reject metadata is refused unless the validator is constructed with test hooks
enabled. Safe-zone and crop rules act only when their profile enables the rule
and an explicit false signal is present; absent signals are not represented as
successful visual inspection.

### Slice 02 manifests

`cloud_fulfillment_manifest.py` sorts identifier lists, serializes compact JSON
with stable key order, and computes a lowercase SHA-256 digest. Deserialization
recomputes the digest with constant-time comparison, so content mutation fails
validation. Manifests are returned inline by the offline service only; storage
and URI resolution remain future work.

---

# §9 — Error Handling

## The 422 Contract

HTTP 422 (Unprocessable Entity) is the enforcement mechanism. When validation fails with blocking errors, the bridge returns 422 with structured violation data. Agents must handle 422 to proceed — there is no workaround.

```
Agent → POST /compile/pwa-icon → Bridge → CLI (validate) → exit 2
                                 Bridge ← JSON violations
Agent ← 422 + violations ← Bridge
```

The 422 response body is always a `ValidationResult` with `valid: false` and a non-empty `violations` array.

## Rust Error Types (`pipeline.rs`)

```rust
#[derive(Debug, thiserror::Error)]
pub enum PipelineError {
    #[error("Template not found: {0}")]
    TemplateNotFound(String),

    #[error("Validation failed")]
    ValidationFailed(ValidationResult),

    #[error("Engine version {engine} < required {required}")]
    EngineVersionMismatch { engine: String, required: String },

    #[error("Compilation error: {0}")]
    CompilationError(String),

    #[error("Serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),
}
```

## Validation Violations

Each violation contains full diagnostic information:

| Field | Type | Purpose |
|-------|------|---------|
| `rule` | string | Which rule produced this (e.g., "aspect_ratio") |
| `severity` | enum | Error, Warning, or Info |
| `message` | string | Human-readable description |
| `expected` | string | What the template requires |
| `actual` | string | What the input provided |
| `remediation` | string[] | Actionable fix suggestions |

### Severity Semantics

| Severity | Blocks in Block mode | Blocks in Warn mode | Blocks in Log mode |
|----------|---------------------|---------------------|-------------------|
| Error | Yes | No | No |
| Warning | No | No | No |
| Info | No | No | No |

## CLI Exit Codes

| Code | Meaning | Stdout | Bridge Action |
|------|---------|--------|---------------|
| 0 | Success | JSON result | Return 200 |
| 1 | System error | Error message | Return 500 |
| 2 | Validation failure | JSON with violations | Return 422 |

The bridge interprets exit code 2 specifically as a validation failure and parses the stdout JSON for violation details.

## Bridge Error Responses

| HTTP Status | Condition | Response Body |
|-------------|-----------|---------------|
| 404 | Template not found | `{"detail": "Template not found: {id}"}` |
| 422 | Validation failure | `ValidationResult` with violations |
| 503 | CLI binary not found | `{"detail": "ForgeImages CLI not available"}` |
| 504 | CLI timeout | `{"detail": "CLI execution timed out"}` |

## Python Exceptions

### Skill-Level Errors

```python
class ForgeImagesError(Exception):
    """Raised when bridge returns non-2xx status."""
    status_code: int
    violations: list[dict]

    def is_validation_error(self) -> bool:
        """True if HTTP 422 (validation failure)."""
        return self.status_code == 422

    def get_remediation_hints(self) -> list[str]:
        """Extract remediation from all violations."""
```

### Error Flow

```
compile() called
  → httpx.post("/compile/{id}")
    → HTTP 422 returned
      → Parse violations from response
      → Raise ForgeImagesError(status_code=422, violations=[...])

validate_and_compile() called
  → validate() called first
    → HTTP 422 returned
      → Return (ValidationResult(valid=False, ...), None)
      → Does NOT raise — caller checks result.valid
```

The `validate_and_compile()` convenience method intentionally does not raise on validation failure. It returns `(result, None)` so agents can inspect violations and decide how to respond.

## Pydantic Validation (Bridge Input)

The bridge validates all inputs before calling the CLI:

| Constraint | Field | Rule |
|------------|-------|------|
| Dimension range | width, height | 1-10000 |
| Color count range | color_count | 1-256 (optional) |
| Template ID format | template_id | `^[a-zA-Z0-9_-]+$` (no path traversal) |
| Prompt length | prompt | Max 2000 characters |
| Seed value | seed | Non-negative integer |

Invalid input is rejected at the Pydantic layer before the CLI is ever invoked.

---

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
| tempfile | 3.0 (dev only) | Test fixtures |

**Rust edition:** 2024
**MSRV:** Follows Rust 2024 edition requirements

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

## Build Tools

| Tool | Purpose |
|------|---------|
| cargo | Rust build + test |
| pip / hatch | Python package management |
| uvicorn | Bridge server |
| pytest | Python tests |

## Feature Flags

| Flag | Purpose |
|------|---------|
| `test-hooks` | Enables test hook points in compilation pipeline |

---

# §8 — Ecosystem Integration

## Integration Map

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  VibeForge   │     │ ForgeAgents  │     │ AuthorForge  │
│ (consumer)   │     │ (orch.)      │     │ (future)     │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       │    ┌───────────────┘                    │
       │    │                                    │
       ▼    ▼                                    ▼
┌──────────────────────────────────────────────────────────┐
│              ForgeImages Skill (httpx)                     │
│         forgeagents-forgeimages/skill/                     │
└────────────────────────┬─────────────────────────────────┘
                         │ HTTP
┌────────────────────────▼─────────────────────────────────┐
│              ForgeImages Bridge (FastAPI)                  │
│         forgeagents-forgeimages/bridge/                    │
└────────────────────────┬─────────────────────────────────┘
                         │ subprocess
┌────────────────────────▼─────────────────────────────────┐
│              ForgeImages Core (Rust)                       │
│         forgeimages-core/                                  │
└──────────────────────────────────────────────────────────┘
```

## ForgeAgents Integration (Active)

### Skill Wrapper

The `ForgeImagesSkill` class in `skill/forgeimages_skill.py` provides the agent-facing interface:

```python
skill = ForgeImagesSkill(bridge_url="http://localhost:8100", user_id="agent-1")

# List templates
templates = await skill.list_templates()

# Validate
result = await skill.validate("pwa-icon", width=512, height=512, color_count=8)
if not result.valid:
    hints = result.violations  # Remediation hints included

# Compile
asset = await skill.compile("pwa-icon", width=512, height=512)
export = asset.get_export("pwa-512")
raw_data = asset.get_export_data("pwa-512")  # Decoded bytes

# Convenience: validate then compile
validation, asset = await skill.validate_and_compile("pwa-icon", width=512, height=512)
```

### Agent Boundary Enforcement

| Allowed | Blocked |
|---------|---------|
| `skill.list_templates()` | Direct file writes |
| `skill.validate(...)` | Template modification |
| `skill.compile(...)` | Validation bypass |
| `skill.get_template(...)` | Failure mode override |

### Error Handling

- `ForgeImagesError` with `status_code` and `violations`
- `is_validation_error()` returns `True` for HTTP 422
- `get_remediation_hints()` extracts remediation from violation list
- `validate_and_compile()` returns `(ValidationResult, None)` on validation failure — does NOT raise

### HTTP Headers

The skill includes `X-User-ID` in all requests (if set at construction), enabling audit trail attribution.

## VibeForge Integration (Planned)

VibeForge is the primary consumer of ForgeImages. The planned integration:

- **Prompt-to-image workflows** — VibeForge generates image candidates via AI, ForgeImages validates and compiles them
- **Tauri IPC** — Future Tauri commands will wrap ForgeImages operations for desktop use
- **Template browsing** — VibeForge UI will display available templates and their constraints

**Status:** Not yet implemented. Requires Tauri command integration.

## AuthorForge Integration (Future)

AuthorForge will use ForgeImages for:

- **Book covers** — Cover template with specific aspect ratios and export formats
- **Print PDF** — CMYK color space via PrintAuthority
- **Chapter illustrations** — Banner/icon templates for digital and print
- **Print bleed** — Physical bleed specifications from PrintSpec

**Status:** Not yet implemented. Requires CMYK export pipeline and print templates.

## DataForge Integration

ForgeImages does not write directly to DataForge. The expected data flow:

1. Agent requests compilation via ForgeImages
2. Agent receives compiled asset (base64 + hashes)
3. Agent persists metadata and results to DataForge

This maintains the DataForge source-of-truth contract while keeping ForgeImages stateless.

## Integration Contracts

### Skill → Bridge Contract

| Property | Value |
|----------|-------|
| Protocol | HTTP/1.1 |
| Content-Type | application/json |
| Auth | None (X-User-ID for audit only) |
| Timeout | 30 seconds (configurable) |
| Retry | Not built-in; caller's responsibility |

### Bridge → CLI Contract

| Property | Value |
|----------|-------|
| Interface | Subprocess (stdin/stdout) |
| Input | JSON via `--payload` flag |
| Output | JSON on stdout |
| Exit 0 | Success |
| Exit 2 | Validation/compilation failure |
| Exit 1 | System error |
| Timeout | 30 seconds |

---

# Scope

**Document version:** 1.0 (bootstrap scaffold)

Scope and authority boundary of this documentation system.

> This chapter is a registry-generated bootstrap scaffold for a
> `documentation` class documentation system. Replace this placeholder with
> real authored content. Registry will not invent repo truth that is not
> already present in the repo.

---

# Governance

**Document version:** 1.0 (bootstrap scaffold)

Ownership, review, and change-authority boundaries.

> This chapter is a registry-generated bootstrap scaffold for a
> `documentation` class documentation system. Replace this placeholder with
> real authored content. Registry will not invent repo truth that is not
> already present in the repo.

---

# Change Control

**Document version:** 1.0 (bootstrap scaffold)

Change-control workflow, proposal lifecycle, and audit.

> This chapter is a registry-generated bootstrap scaffold for a
> `documentation` class documentation system. Replace this placeholder with
> real authored content. Registry will not invent repo truth that is not
> already present in the repo.

---

# §5 — Configuration & Environment

## Bridge Environment Variables

All bridge configuration uses the `FORGEIMAGES_` prefix via pydantic-settings.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `FORGEIMAGES_CLI_PATH` | Path | `../forgeimages-core/target/release/forgeimages-cli` | Path to compiled Rust CLI binary |
| `FORGEIMAGES_TEMPLATES_DIR` | Path | `../forgeimages-core/templates` | Directory containing template JSON files |
| `FORGEIMAGES_AUDIT_LOG_PATH` | Path | `./audit.jsonl` | Audit log output file |
| `FORGEIMAGES_MAX_REQUEST_SIZE_MB` | int | `10` | Maximum HTTP request body size |
| `FORGEIMAGES_MAX_PAYLOAD_SIZE_KB` | int | `512` | Maximum JSON payload size |
| `FORGEIMAGES_ENGINE_VERSION` | str | `"1.0.0"` | Engine version for audit logging |

## CLI Flags

### Global Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--templates-dir` | `templates` | Directory containing template JSON files |

### Validate Subcommand

| Flag | Required | Description |
|------|----------|-------------|
| `--template` | Yes | Template ID to validate against |
| `--payload` | Yes | JSON string of AssetInput |

### Compile Subcommand

| Flag | Required | Description |
|------|----------|-------------|
| `--template` | Yes | Template ID to compile against |
| `--payload` | Yes | JSON string of CompileRequest |

## Template Configuration (pwa-icon.json)

Templates are JSON files in the templates directory. Each template defines:

```json
{
  "id": "pwa-icon",
  "name": "PWA Icon Pack",
  "templateVersion": "1.0.0",
  "engineMinVersion": "1.0.0",
  "assetClass": "icon",
  "aspectRatio": [1, 1],
  "canonicalSize": [1024, 1024],
  "vectorMaster": true,
  "validation": {
    "required": true,
    "failureMode": "block",
    "rules": {
      "aspectRatio": { "enabled": true, "tolerance": 0.01 },
      "resolution": { "enabled": true, "minWidth": 512, "minHeight": 512 },
      "colorCount": { "enabled": true, "maxColors": 16 }
    }
  },
  "exports": [
    { "id": "master", "size": [1024, 1024], "format": "svg", "required": true },
    { "id": "favicon-16", "size": [16, 16], "format": "png", "required": true },
    { "id": "favicon-32", "size": [32, 32], "format": "png", "required": true },
    { "id": "apple-touch", "size": [180, 180], "format": "png", "required": true },
    { "id": "pwa-192", "size": [192, 192], "format": "png", "required": true },
    { "id": "pwa-512", "size": [512, 512], "format": "png", "required": true }
  ]
}
```

## Rust Constants

| Constant | Value | Location |
|----------|-------|----------|
| `ENGINE_VERSION` | `env!("CARGO_PKG_VERSION")` → `"1.0.0"` | `lib.rs` |
| `MIN_TEMPLATE_VERSION` | `"1.0.0"` | `lib.rs` |

## Default Validation Tolerances

| Rule | Default | Description |
|------|---------|-------------|
| Aspect ratio tolerance | 0.01 (1%) | Quantization bucket for ratio comparison |
| Min resolution | 1024x1024 | Default minimum (overridden by template) |
| Max color count | 16 | Default maximum (overridden by template) |

## Print Defaults

| Setting | Default | Valid Range |
|---------|---------|-------------|
| DPI | 300 | 72-1200 |
| Color space | RGB | RGB, CMYK, Grayscale |
| Bleed | 0.125 inches | 0-1 inch |

---

# §10 — Testing

## Test Suite Overview

| Layer | Tests | File | Framework |
|-------|-------|------|-----------|
| Rust invariants | 6 | `forgeimages-core/tests/invariants.rs` | cargo test |
| Rust core | 48 | inline + `forgeimages-core/tests/` | cargo test |
| Python agent boundaries | 18 | `forgeagents-forgeimages/tests/test_agent_boundary.py` | pytest |
| Cloud validation contracts | 18 | `test_forgeimages_validation_contracts.py`, `test_forgeimages_rejection_report_contract.py` | pytest |
| Cloud validator and manifests | 14 | `test_forgeimages_asset_validator.py`, `test_forgeimages_asset_manifest.py` | pytest |

## Rust Invariant Tests

These tests verify the Six Laws are enforced in code. They are non-negotiable.

### `invariant_compile_calls_validate`
Verifies that `compile_asset()` always invokes validation. An invalid asset must be rejected even when calling compile directly. This is the single most important test in the system.

### `invariant_valid_asset_compiles`
A valid 512x512 asset with 8 colors compiles successfully against the pwa-icon template. The result includes all 6 exports.

### `invariant_manifest_hash_stable`
Same inputs produce the same job_hash across multiple invocations. This verifies deterministic output.

### `invariant_canonical_json_deterministic`
JSON with keys in different insertion orders produces identical canonical output. This verifies cross-platform hash stability.

### `invariant_template_not_found_error`
Requesting a non-existent template returns `PipelineError::TemplateNotFound`.

### `invariant_validation_result_structure`
The `ValidationResult` struct has the required fields: `valid`, `violations`, `template_id`, `template_version`.

### Rust Inline Tests (hashing.rs)

- `test_canonical_json_sorted` — Keys are sorted alphabetically
- `test_hash_deterministic` — Same input = same SHA-256
- `test_manifest_hash_stable` — Manifest hash doesn't drift

## Python Boundary Tests

These tests verify that agents cannot bypass ForgeImages' enforcement mechanisms.

### Test Classes

**TestValidationEnforcement** (2 tests)
- Invalid aspect ratio returns 422
- Compile fails on validation error

**TestValidationResult** (2 tests)
- Error detection (`has_errors`)
- Warning detection (`has_warnings`)

**TestForgeImagesError** (2 tests)
- HTTP 422 identified as validation error
- Non-422 errors handled correctly

**TestAssetInputValidation** (4 tests)
- Valid dimensions accepted
- Negative dimensions rejected
- Zero dimensions rejected
- Dimensions >10000 rejected

**TestCompileRequestValidation** (3 tests)
- Valid template ID format accepted
- Path traversal in template ID rejected (`../evil`)
- Spaces in template ID rejected

**TestSkillInterface** (2 tests)
- `validate_and_compile` stops on invalid input (returns None)
- `X-User-ID` header included when user_id is set

**TestNoBypassPossible** (3 tests)
- CompileRequest requires asset_input
- AssetInput requires dimensions
- Skill always calls bridge (no local bypass)

## Cloud-Fulfillment Contract Tests

The Slice 01 tests prove that:

- request and result schema versions are required and exact
- every top-level transport envelope field is required
- naive timestamps and unrecognized fields fail closed
- result counts cannot diverge from accepted/rejected record lists
- all 15 governed rejection codes round-trip as enums
- unknown rejection codes fail closed
- rejection guidance survives JSON round trips
- the contract module imports without generation-provider dependencies

## Cloud Validator and Manifest Tests

The Slice 02 tests prove that:

- valid artifacts are accepted while unsupported formats, low resolution, and
  bad aspect ratio receive stable rejection codes
- production-configured services reject test-only metadata
- force-reject, safe-zone, and crop placeholder signals are deterministic
- replacement counts include only hard failures
- validation and idempotency identifiers are stable
- manifest list ordering and hashing are deterministic
- tampered manifest content fails digest verification
- validator/profile/manifest modules have no generation-client imports

## Running Tests

```bash
# Rust tests (all)
cd forgeimages-core && cargo test

# Rust invariant tests only
cd forgeimages-core && cargo test --test invariants

# Python tests
cd forgeagents-forgeimages && pytest tests/ -v

# Cloud-fulfillment Slice 01 only
cd forgeagents-forgeimages && \
  pytest tests/test_forgeimages_validation_contracts.py \
         tests/test_forgeimages_rejection_report_contract.py -q

# Cloud-fulfillment Slice 02 only
cd forgeagents-forgeimages && \
  pytest tests/test_forgeimages_asset_validator.py \
         tests/test_forgeimages_asset_manifest.py -q

# Python tests with coverage
cd forgeagents-forgeimages && pytest tests/ -v --cov=bridge --cov=skill
```

## Test Philosophy

1. **Invariant tests verify laws, not features.** Each test maps to one of the Six Laws.
2. **Boundary tests verify trust boundaries.** Each test verifies that agents cannot bypass enforcement.
3. **No mocks of the core engine.** Bridge tests may mock the CLI subprocess, but invariant tests use the real pipeline.
4. **Exit code 2 is sacred.** Tests verify that validation failures always produce exit code 2, never exit code 1 or 0.

---

# §11 — Handover

## Critical Constraints (Non-Negotiable)

1. **`compile_asset()` ALWAYS calls `validate_asset()`.** No code path may bypass this. If you add a new compilation method, it must validate first.

2. **Templates are immutable contracts.** Once a template version is published, it cannot be modified. Create a new version instead.

3. **Exit code 2 means validation failure.** The bridge depends on this contract. Do not change CLI exit code semantics.

4. **Audit log is append-only.** Never modify, truncate, or rotate the JSONL audit log in production. Only append.

5. **No file paths cross the trust boundary.** All asset data is base64-encoded. Agents receive data, not paths.

6. **Canonical JSON is the hashing input.** All hashes use `canonical_json()` — sorted keys, no whitespace. Do not hash raw JSON.

7. **HTTP 422 is the enforcement mechanism.** Agents cannot proceed past a 422. Do not change this to 400 or 200-with-errors.

## Deployment

### Rust Core

```bash
cd forgeimages-core
cargo build --release
# Binary: target/release/forgeimages-cli
```

### Bridge Service

```bash
cd forgeagents-forgeimages
pip install -e .
uvicorn bridge.forgeimages_bridge:app --host 127.0.0.1 --port 8100
```

### Verification

```bash
# Health check
curl http://localhost:8100/health

# List templates
curl http://localhost:8100/templates

# Validate (should return 200 with valid: true)
curl -X POST http://localhost:8100/validate/pwa-icon \
  -H "Content-Type: application/json" \
  -d '{"width": 512, "height": 512, "color_count": 8}'

# Validate (should return 422 with violations)
curl -X POST http://localhost:8100/validate/pwa-icon \
  -H "Content-Type: application/json" \
  -d '{"width": 1024, "height": 512}'
```

## Implementation Status

- [x] Core Rust library (`forgeimages-core` v1.0.0)
- [x] Template system (`templates.rs` + `pwa-icon.json`)
- [x] Validation pipeline (3 rules + failure mode policy)
- [x] SHA-256 manifest generation (canonical JSON, job_hash, manifest_hash)
- [x] PrintAuthority enum (System/Template/User with DPI/CMYK support)
- [x] Compilation pipeline (compile always validates, no bypass)
- [x] CLI binary (templates, validate, compile subcommands)
- [x] Bridge service (5 FastAPI endpoints)
- [x] Skill wrapper (async httpx client with error handling)
- [x] Audit logging (append-only JSONL with job_hash)
- [x] Invariant tests (6 Rust contract tests)
- [x] Boundary tests (18 Python enforcement tests)
- [x] Cloud-fulfillment Slice 01 validation and rejection contracts
- [x] Cloud-fulfillment Slice 02 deterministic validator and manifest model
- [ ] Tauri integration for VibeForge
- [ ] MCP tool definitions

The Slice 01/02 cloud-fulfillment components are offline seams: no
NeuroForge-facing validation route, artifact-byte retrieval, durable manifest
store, Rust compiler integration, or replacement loop is implemented. The next
governed work is the cross-repository replacement-feedback Slice 03, initially
using stubs and mocks.

## Future Work

### Tauri Integration (VibeForge)

Wrap ForgeImages operations as Tauri commands for desktop use. The bridge service would be replaced by direct Rust library calls from the Tauri backend.

### MCP Tool Definitions

Define MCP tools for ForgeImages operations, enabling AI agents to discover and invoke ForgeImages capabilities via the Model Context Protocol.

### Additional Templates

- Book cover template (AuthorForge)
- Banner template (marketing assets)
- Logo template (brand assets)

### CMYK Export Pipeline

Full CMYK support for print production, leveraging the PrintAuthority system already in place.

## Adding a New Template

1. Create a JSON file in `forgeimages-core/templates/` following the pwa-icon.json structure
2. Set `templateVersion` to "1.0.0" and `engineMinVersion` to the current engine version
3. Define validation rules (aspect ratio, resolution, color count)
4. Define export specifications (format, size, required flag)
5. Run `cargo test` to verify the template loads correctly
6. Test via CLI: `forgeimages-cli validate --template <id> --payload '...'`

## Adding a New Validation Rule

1. Define a struct implementing the `ValidationRule` trait in `validation.rs`
2. Implement `name()` and `validate()` methods
3. Add the rule to the `Validator` struct's rule list
4. Add invariant tests in `tests/invariants.rs`
5. Add boundary tests in `tests/test_agent_boundary.py`
6. Update this documentation (§7 and §10)

---

# §4 — Project Structure

## Directory Tree

```
ForgeImages/
├── README.md                          # Project overview and quick start
├── CLAUDE.md                          # AI assistant coding standards
├── .gitignore                         # Build artifacts, venvs, audit logs
│
├── doc/                               # Forge Documentation Protocol docs
│   ├── system/                        # Modular system documentation parts
│   │   ├── _index.md                  # Master table of contents
│   │   ├── 01-overview-philosophy.md  # §1: Six Laws, ecosystem role
│   │   ├── 02-architecture.md         # §2: Trust boundary, data flow
│   │   ├── 03-tech-stack.md           # §3: Dependencies and versions
│   │   ├── 04-project-structure.md    # §4: This file
│   │   ├── 05-config-env.md           # §5: Environment and CLI flags
│   │   ├── 06-api-layer.md            # §6: Bridge endpoints, CLI commands
│   │   ├── 07-backend-internals.md    # §7: Template, validation, hashing, pipeline
│   │   ├── 08-ecosystem-integration.md # §8: ForgeAgents, VibeForge, AuthorForge
│   │   ├── 09-error-handling.md       # §9: 422 contract, exit codes, violations
│   │   ├── 10-testing.md             # §10: Invariant + boundary tests
│   │   ├── 11-handover.md            # §11: Constraints, deployment, future
│   │   └── BUILD.sh                   # Assembles parts into context-bundle.md
│   └── SYSTEM.md                      # Generated: full assembled reference
│
├── scripts/
│   └── context-bundle.sh             # AI session context generator (presets)
│
├── files/                             # Design documentation (pre-implementation)
│   ├── README.md                      # ForgeAgents integration guide
│   ├── CONTEXT.md                     # Trust boundary architecture
│   ├── step1-rust-core.md             # Rust core design spec
│   ├── step2-rust-cli.md              # CLI design spec
│   ├── step3-python-bridge.md         # Bridge service design spec
│   ├── step4-python-skill.md          # Skill wrapper design spec
│   ├── step5-tests.md                 # Test strategy spec
│   └── VSCODE_CLAUDE_PROMPT.md        # Implementation prompt
│
├── forgeimages-core/                  # Rust core engine
│   ├── Cargo.toml                     # Package: forgeimages-core v1.0.0, edition 2024
│   ├── src/
│   │   ├── lib.rs                     # Library root — Six Laws, public API exports
│   │   ├── templates.rs               # Template contracts (TemplateRegistry, AssetClass, ExportSpec)
│   │   ├── validation.rs              # Rule/policy separation (3 rules, Validator, FailureMode)
│   │   ├── hashing.rs                 # SHA-256 manifests (canonical JSON, job_hash, manifest_hash)
│   │   ├── print.rs                   # PrintAuthority enum (System/Template/User, DPI/CMYK)
│   │   ├── pipeline.rs               # CompilationPipeline (compile ALWAYS validates, exports)
│   │   └── bin/
│   │       └── forgeimages_cli.rs     # CLI binary (templates, validate, compile subcommands)
│   ├── templates/
│   │   └── pwa-icon.json              # PWA icon template (1:1, 512px min, 6 PNG + 1 SVG)
│   └── tests/
│       └── invariants.rs              # Contract invariant tests (6 tests)
│
└── forgeagents-forgeimages/           # Python agent integration
    ├── pyproject.toml                 # Package: forgeagents-forgeimages v1.0.0, Python >=3.10
    ├── bridge/                        # FastAPI bridge service
    │   ├── __init__.py                # Package init
    │   ├── forgeimages_bridge.py      # HTTP endpoints (health, templates, validate, compile)
    │   ├── models.py                  # Pydantic v2 models (AssetInput, CompileRequest, etc.)
    │   ├── settings.py                # Configuration (FORGEIMAGES_ env prefix)
    │   └── audit.py                   # Append-only JSONL audit logging
    ├── skill/                         # ForgeAgents skill wrapper
    │   ├── __init__.py                # Package init
    │   └── forgeimages_skill.py       # ForgeImagesSkill class (async httpx client)
    └── tests/
        └── test_agent_boundary.py     # Agent boundary enforcement tests (20+ tests)
```

## Key Module Responsibilities

### Rust Modules

| Module | LOC | Responsibility |
|--------|-----|----------------|
| `lib.rs` | 25 | Six Laws docstring, public API re-exports, version constants |
| `templates.rs` | 176 | Template, AssetClass, ValidationConfig, ExportSpec, TemplateRegistry |
| `validation.rs` | 224 | 3 rules (AspectRatio, Resolution, ColorCount), Validator, FailureMode |
| `hashing.rs` | 102 | SHA-256, canonical JSON (sorted keys), job_hash, manifest_hash |
| `print.rs` | 81 | PrintAuthority enum, PrintSpec, ColorSpace, DPI/bleed validation |
| `pipeline.rs` | 272 | CompilationPipeline, CompileRequest, CompiledAsset, ExportedFile |
| `forgeimages_cli.rs` | 149 | Clap CLI: templates, validate (exit 2), compile (exit 2) |

### Python Modules

| Module | LOC | Responsibility |
|--------|-----|----------------|
| `models.py` | 93 | Pydantic v2 models mirroring Rust types |
| `settings.py` | 33 | Environment-based config (FORGEIMAGES_ prefix) |
| `audit.py` | 105 | Append-only JSONL audit log with job hash linkage |
| `forgeimages_bridge.py` | 272 | FastAPI app with 5 endpoints, CLI subprocess calls |
| `forgeimages_skill.py` | 378 | ForgeImagesSkill class, async httpx, error handling |

---

---

# Appendices

**Document version:** 1.0 (carry-forward)

Appendices, glossary, and cross-references.

## Unmapped legacy chapters

The following legacy chapters were carried forward but could not be
deterministically mapped to a class-aware slot. Review and place them by
hand:

- `ForgeImages System Documentation`
- `§3 — Tech Stack`
- `§5 — Configuration & Environment`
- `§6 — API Layer`
- `§7 — Backend Internals`
- `§8 — Ecosystem Integration`
- `List templates`
- `Validate`
- `Compile`
- `Convenience: validate then compile`
- `§9 — Error Handling`
- `§10 — Testing`
- `Rust tests (all)`
- `Rust invariant tests only`
- `Python tests`
- `Python tests with coverage`
- `§11 — Handover`
- `Binary: target/release/forgeimages-cli`
- `Health check`
- `List templates`
- `Validate (should return 200 with valid: true)`
- `Validate (should return 422 with violations)`

---

# §1 — Overview & Philosophy

## Service Identity

**ForgeImages** is the template-driven image asset pipeline for the Forge Ecosystem. It provides deterministic, auditable image asset generation with strict validation enforcement and a clear separation between agent suggestions and system enforcement.

- **Version:** v1.0.0
- **Status:** Implemented (core engine + bridge + skill)
- **Languages:** Rust 2024 (core engine + CLI), Python 3.10+ (agent bridge + skill)
- **LOC:** ~2,400 (Rust ~1,100, Python ~800, Tests ~500)

## The Six Laws (Non-Negotiable)

These are the canonical invariants. Every code path, every test, every design decision traces back to one of these laws.

1. **SVG Is Truth** — Vector masters are the canonical source; all raster exports derive from them.
2. **Templates Are Contracts** — Old templates work forever. New engines never silently change behavior. Version mismatch = clear error.
3. **Validation Is Protective** — Validation exists to catch errors before they propagate, not to punish users.
4. **Deterministic Output** — Same inputs always produce the same outputs. Manifest hashes are stable and reproducible.
5. **Manifests Enable Reproduction** — SHA-256 hashes link inputs to outputs for legal defensibility and auditability.
6. **Agents Suggest, Engine Enforces** — AI agents can generate and select candidates, but all validation and compilation must pass through ForgeImages' template-defined rules. No bypasses allowed.

## Core Principle

> **Agents suggest, ForgeImages enforces.**

This is not a guideline. It is an architectural invariant enforced at three levels:

1. **Rust type system** — `compile_asset()` always calls `validate_asset()` internally
2. **HTTP status codes** — Bridge returns 422 on validation failure; agents cannot proceed
3. **CLI exit codes** — Exit code 2 = validation failure; bridge interprets this as 422

## Ecosystem Role

```
┌──────────────────────────────────────────────────────────────┐
│                      Forge Ecosystem                          │
│                                                              │
│   VibeForge     ForgeAgents     AuthorForge                 │
│   (consumer)    (orchestration)  (future)                    │
│       │              │              │                        │
│       └──────────────┴──────────────┘                        │
│                      │                                       │
│          ┌───────────▼────────────┐                          │
│          │   ForgeImages Bridge   │  ← HTTP gateway          │
│          │   (Python / FastAPI)   │                          │
│          └───────────┬────────────┘                          │
│                      │ subprocess                            │
│          ┌───────────▼────────────┐                          │
│          │   ForgeImages Core     │  ← Validation + compile  │
│          │   (Rust 2024)          │                          │
│          └────────────────────────┘                          │
└──────────────────────────────────────────────────────────────┘
```

## What ForgeImages Is

- **A validation engine** — Enforces template-defined rules on image assets
- **A compilation pipeline** — Produces deterministic, hashed export bundles
- **An audit trail** — Every request is logged with job hashes linking inputs to outputs
- **A trust boundary** — Agents interact through the skill/bridge layer; they never touch the engine directly

## What ForgeImages Is Not

- **Not an image editor.** It does not provide editing tools; it validates and compiles assets.
- **Not a storage service.** Compiled assets are returned as base64; persistence is the caller's responsibility.
- **Not an AI model.** It does not generate images; agents upstream (VibeForge) handle generation.
- **Not a CDN.** It produces export bundles; distribution is handled elsewhere.

## Codebase Metrics

| Metric | Count |
|--------|-------|
| Rust source files | 7 (lib + 5 modules + CLI) |
| Python source files | 6 (bridge: 4, skill: 1, init: 1) |
| Test files | 2 (Rust invariants + Python boundaries) |
| Template files | 1 (pwa-icon.json) |
| Validation rules | 3 (AspectRatio, Resolution, ColorCount) |
| CLI subcommands | 3 (templates, validate, compile) |
| Bridge endpoints | 5 (health, templates, template/:id, validate/:id, compile/:id) |
| Test methods | 26+ (Rust: 6 invariant, Python: 20+ boundary) |

---

---

# §2 — Architecture

## Three-Tier Trust Boundary

ForgeImages enforces a strict three-tier architecture where each layer has defined responsibilities and no layer can bypass the one below it.

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  ForgeAgents    │────▶│  Bridge Service  │────▶│  ForgeImages    │
│  (Python)       │     │  (FastAPI)       │     │  Core (Rust)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                        │                        │
   Skill Call             Audit Log              Validation
   (httpx)               HTTP 422               Enforced
```

### Layer 1: Agent Skill (Python — `skill/`)

The agent-facing interface. Provides async methods for template listing, validation, and compilation. Communicates exclusively via HTTP to the bridge service.

**Agents CAN:**
- Generate image candidates
- Select candidates
- Request compilation
- List available templates

**Agents CANNOT:**
- Skip validation
- Override templates
- Write files directly
- Change failure mode

### Layer 2: Bridge Service (Python — `bridge/`)

The HTTP gateway between agents and the Rust engine. Handles request validation (Pydantic v2), audit logging (append-only JSONL), and subprocess management (CLI invocation).

**Bridge responsibilities:**
- Pydantic input validation (dimensions 1-10000, template ID format)
- Audit logging with job hash linkage
- CLI subprocess execution with 30-second timeout
- Structured error responses (422 with violations + remediation)
- Request size limiting

### Layer 3: Core Engine (Rust — `forgeimages-core/`)

The validation and compilation engine. Template contracts, validation rules, SHA-256 manifest generation, and export rendering. This is the enforcement layer.

**Engine guarantees:**
- `compile_asset()` ALWAYS calls `validate_asset()` — no code path bypasses this
- Template version compatibility is checked via semver
- All outputs include deterministic manifest hashes
- Canonical JSON ensures hash stability across platforms

## Data Flow: Compile Request

```
Agent                   Bridge                    Engine
  │                       │                         │
  │──POST /compile/X────▶│                         │
  │                       │──call_cli(compile)────▶│
  │                       │                         │──validate_asset()
  │                       │                         │──check_engine_version()
  │                       │                         │──generate_exports()
  │                       │                         │──compute_job_hash()
  │                       │◀──JSON + exit code──────│
  │                       │──audit_log.log()        │
  │◀──200 CompiledAsset──│                         │
  │   or 422 violations   │                         │
```

## Data Flow: Validation Failure

```
Agent                   Bridge                    Engine
  │                       │                         │
  │──POST /validate/X───▶│                         │
  │                       │──call_cli(validate)───▶│
  │                       │                         │──run 3 rules
  │                       │                         │──apply failure_mode
  │                       │◀──exit code 2 + JSON───│
  │                       │──audit_log.log()        │
  │◀──422 + violations───│                         │
  │                       │                         │
  │  (agent CANNOT        │                         │
  │   proceed past 422)   │                         │
```

## PrintAuthority Model

The PrintAuthority enum determines the source of physical output specifications:

```
PrintAuthority::System    → Default (300 DPI, RGB, 0.125" bleed)
PrintAuthority::Template  → Template-defined specs
PrintAuthority::User      → User-provided (validated: 72-1200 DPI, 0-1" bleed)
```

This eliminates conditional sprawl — the enum determines behavior, not nested if/else chains.

## Template Contract Model

Templates are JSON files that define:
- Asset class (Icon, Cover, Banner, Logo)
- Aspect ratio with quantization tolerance
- Minimum resolution constraints
- Color count limits
- Export specifications (format, size, required flag)
- Failure mode (Block, Warn, Log)
- Engine version compatibility

Templates are versioned via semver. The engine checks `engineMinVersion` against `ENGINE_VERSION` before processing.

## Key Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| Rust core, Python bridge | Rust for determinism + safety; Python for agent ecosystem integration |
| CLI subprocess (not FFI) | Clean process boundary; exit codes are the enforcement mechanism |
| HTTP 422 for validation | Standard HTTP semantics; agents must handle 422 to proceed |
| Append-only audit log | Legal defensibility; no mutation of historical records |
| Base64 export data | No file paths cross the trust boundary; data is self-contained |
| Canonical JSON hashing | Platform-independent determinism for manifest verification |

---

# ForgeImages — Compiled System Reference

**Designation:** img
**Document role:** Canonical compiled technical reference for the ForgeImages asset validation and compilation pipeline
**Source:** `doc/system/`
**Build command:** `bash doc/system/BUILD.sh`
**Document version:** 3.0 (2026-10-30) — canonicalized to the Forge_Command doc-system shape
**Protocol:** BDS Documentation Protocol v2.0; BDS Repo Documentation System Canonical Compliance Standard

> **Generated artifact warning:** `doc/imgSYSTEM.md` is assembled output. Edit
> the source modules under `doc/system/` and rebuild. Hand edits to the
> compiled artifact are overwritten by the next build.

Assembly contract:

- Command: `bash doc/system/BUILD.sh`
- Validation: `bash doc/system/validate_snapshots.sh` runs during assembly
- Machine source map: `doc/system/system_manifest.json`
- Primary output: `doc/imgSYSTEM.md`

This `doc/system/` tree is the canonical source of truth for ForgeImages
(`Boswell-Digital-Solutions/forgeimages`, the repository AuthorForge vendors as
`third_party/forgeimages`). It is not the documentation for the separate
`Forge_Images` repository (designation `ima`). It uses explicit **truth
classes**: *canonical facts* define role, the Six Laws, authority boundaries,
contracts and invariants; *snapshot facts* are dated, audit-derived counts and
inventories (files, lines, tests, templates, gaps) that drift between audits.
See §15 for the scope and authority order.

`system_manifest.json` is the fail-closed, machine-readable map from owned
repository surfaces to chapters, agent profiles, truth classes and maintenance
triggers. `_index.md` remains the human navigation authority. The build fails if
the two disagree.

| Part | File | Contents |
| --- | --- | --- |
| §1 | `01-overview-philosophy.md` | Service identity, Six Laws, ecosystem role, metrics |
| §2 | `02-architecture.md` | Trust boundary, entry paths, data flow, key decisions |
| §3 | `03-tech-stack.md` | Rust, Tauri, Python and freeze dependencies |
| §4 | `04-project-structure.md` | Directory tree, module responsibilities |
| §5 | `05-config-env.md` | Environment variables, CLI flags, defaults |
| §6 | `06-api-layer.md` | Bridge HTTP endpoints, models, cloud-fulfillment contracts, CLI |
| §7 | `07-tauri-command-interface.md` | Tauri IPC commands consumed by AuthorForge |
| §8 | `08-backend-internals.md` | Templates, validation, source masters, PDF writer, pipeline, hashing, audit |
| §9 | `09-ecosystem-integration.md` | AuthorForge, ForgeAgents, NeuroForge, DataForge contracts |
| §10 | `10-error-handling.md` | 422 contract, error types, exit codes, bridge responses |
| §11 | `11-testing.md` | Test inventory, invariants, running tests |
| §12 | `12-frozen-sidecar.md` | Frozen `forgeimages-bridge` sidecar build and runtime contract |
| §13 | `13-handover.md` | Critical constraints, deployment, status, extension procedures |
| §14 | `14-future-work-tally.md` | Known gaps and deferred work |
| §15 | `15-scope.md` | Scope, truth classes, authority order |
| §16 | `16-governance.md` | Ownership, designation, authority boundaries |
| §17 | `17-change-control.md` | Change workflow, maintenance triggers, defect records |
| §18 | `18-appendices.md` | Glossary, cross-references, revision history |

## Quick Assembly

```bash
bash doc/system/BUILD.sh
```

---

# §1 — Overview & Philosophy

> **System identity — bds family (Boswell Digital Solutions business system, local-systems tier).** ForgeImages is the template-driven image asset pipeline for the Forge ecosystem, implemented as a Rust engine with a Python bridge in `ecosystem/local-systems`.

## Service Identity

**ForgeImages** validates and compiles image assets against versioned template contracts. Every compile produces hashed exports and a manifest that ties the output to its inputs. AI systems may generate and select candidates. ForgeImages decides whether a candidate is admissible and produces the deliverable files.

| Property | Value |
| --- | --- |
| Designation | `img` (registered in the forge meta-repo `doc/PREFIX_REGISTRY.md`) |
| Engine version | `1.0.0` (`forgeimages-core`, `ENGINE_VERSION`) |
| Languages | Rust 2024 (engine, CLI, Tauri commands); Python 3.10+ (bridge, skill, cloud-fulfillment contracts) |
| Deployment | Library inside the AuthorForge desktop app, plus a frozen HTTP sidecar (`forgeimages-bridge`) in AuthorForge release bundles |
| Network posture | Bridge binds loopback only (`127.0.0.1:8100`) and has no authentication |
| State | Stateless, apart from the append-only audit log the bridge writes |

Not to be confused with `Forge_Images` (underscore, designation `ima`), a separate repository with a different git remote whose code has forked from this one. AuthorForge vendors **this** repository as the `third_party/forgeimages` submodule.

## The Six Laws (Non-Negotiable)

These are the canonical invariants. Every code path, test and design decision traces back to one of them.

1. **SVG Is Truth.** Vector masters are the canonical source. Raster exports derive from them.
2. **Templates Are Contracts.** Old templates keep working. A new engine never silently changes behavior. A version mismatch is a clear error.
3. **Validation Is Protective.** Validation catches errors before they spread. It is not there to punish users.
4. **Deterministic Output.** The same inputs always produce the same output bytes and the same hashes.
5. **Manifests Enable Reproduction.** SHA-256 hashes link inputs to outputs, for audit and legal defensibility.
6. **Agents Suggest, Engine Enforces.** Agents can generate and select candidates. Every validation and compilation goes through the template-defined rules. Nothing bypasses them.

Two working rules follow from the laws and appear throughout the code:

- **A supplied master is never silently ignored.** If a caller's master cannot be decoded, is not admissible, or cannot produce a required export, the compile fails. It does not fall back to a placeholder (§8, `source_master.rs`).
- **ForgeImages does not invent.** It does not generate imagery, and it does not perform colour-managed RGB→CMYK conversion. A conversion it cannot do honestly is refused by name (§8, `pdf.rs`).

## Core Principle

> **Agents suggest, ForgeImages enforces.**

The principle is enforced in three places:

1. **The engine.** `compile_asset()` always calls `validate_asset()` first. No code path skips it.
2. **The CLI.** Exit code `2` means a validation or compilation failure.
3. **The bridge.** Exit code `2` becomes HTTP `422`. An agent cannot proceed past a 422.

## Ecosystem Role

```
 NeuronForge Local image lane      AuthorForge desktop (Tauri)
 (diffusion masters)               (cover / asset validation UI)
          │ HTTP                              │ in-process Rust calls
          ▼                                   ▼
 ┌────────────────────────┐        ┌──────────────────────────┐
 │ forgeimages-bridge     │        │ forgeimages-tauri        │
 │ FastAPI, port 8100     │        │ 3 IPC commands           │
 │ frozen sidecar         │        └────────────┬─────────────┘
 └───────────┬────────────┘                     │
             │ subprocess, payload on stdin      │
             ▼                                   ▼
 ┌──────────────────────────────────────────────────────────┐
 │ forgeimages-core (Rust): templates, validation, source    │
 │ masters, PDF/X-1a writer, hashing, compilation pipeline   │
 └──────────────────────────────────────────────────────────┘
```

ForgeAgents reaches the bridge through the `ForgeImagesSkill` client. NeuroForge cloud fulfillment has versioned contracts and an offline validator in the bridge package. No HTTP route serves them yet (§9).

## What ForgeImages Is

- **A validation engine.** It enforces template-defined rules on image assets.
- **A compilation pipeline.** It produces deterministic, hashed export bundles from a caller's master.
- **A print writer.** It writes structurally conformant PDF/X-1a:2001 files. Today the compile path admits only opaque 8-bit grayscale raster masters. The writer can represent CMYK, but no ingest path produces it yet.
- **An audit trail.** The bridge logs every validate and compile request with a job hash.
- **A trust boundary.** Agents reach the engine only through the skill and the bridge. No file paths cross that boundary.

## What ForgeImages Is Not

- **Not an image generator.** Diffusion and other generative work happen upstream, in NeuronForge Local or NeuroForge.
- **Not an image editor.** It validates, converts and packages. It does not retouch.
- **Not a colour-management system.** It refuses RGB masters for PDF/X-1a instead of converting them.
- **Not a storage service.** Exports are returned as base64. The caller persists them.
- **Not an SVG rasterizer.** This repository has no SVG→raster renderer. An SVG master can only produce SVG exports (§14).

## Codebase Metrics

> Snapshot fact, counted 2026-10-30 at the commit this chapter was written against. Recount before you rely on it.

| Metric | Count |
| --- | --- |
| Rust source files (`forgeimages-core/src`, `forgeimages-tauri/src`) | 21 files, 3,179 lines |
| Python source files (`bridge/`, `skill/`) | 11 files, 1,656 lines |
| Template contracts (`forgeimages-core/templates/`) | 5 |
| Rules wired into the default `Validator` | 3 (aspect ratio, resolution, colour count) |
| CLI subcommands | 3 (`templates`, `validate`, `compile`) |
| Bridge HTTP endpoints | 5 |
| Tauri IPC commands | 3 |
| Rust tests (`cargo test --workspace`) | 51, all passing (§11) |
| Python tests (`pytest tests/`) | 52, all passing (§11) |

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

## Two Entry Paths into the Engine

The engine has two callers, and they reach it differently:

| Path | Caller | How it reaches `forgeimages-core` | Operations |
| --- | --- | --- | --- |
| HTTP sidecar | NeuronForge Local image lane, ForgeAgents skill | `forgeimages-bridge` (FastAPI) runs `forgeimages-cli` as a subprocess and sends the JSON payload on stdin | list templates, validate, compile |
| Desktop in-process | AuthorForge Tauri app | `forgeimages-tauri` links the crate directly. Commands are registered in AuthorForge's `src-tauri/src/main.rs` | list templates, validate a file on disk, validate metadata |

The desktop path has no compile command. The Tauri path reads a real file from disk (`validate_from_file`), so a file path crosses into the engine there. That is inside the desktop app's own process, not across the agent trust boundary. No agent reaches the Tauri commands.

## Data Flow: Compile Request

```
Agent                   Bridge                    Engine
  │                       │                         │
  │──POST /compile/X────▶│                         │
  │                       │──call_cli(compile)────▶│  payload on stdin
  │                       │                         │──validate_asset()
  │                       │                         │──check_engine_version()
  │                       │                         │──source_master::decode()
  │                       │                         │──check_admissible()
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
- Asset class (`icon`, `cover`, `banner`, `logo`, `map`, `panel`, `character_portrait`, `scene_illustration`, `marketing_social`)
- Whether the template requires a vector master (`vectorMaster`)
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
| Payload on stdin (`--payload -`) | A base64 raster master is megabytes; Linux caps one argument at 128 KiB and Windows the whole command line at 32 KiB (KI-IMG-20261017-001) |
| Tauri crate links the engine directly | The desktop app validates local files without running the HTTP sidecar |
| Supplied master is authoritative | A master that cannot be honoured fails the compile; it never falls back to a placeholder |
| Hand-written PDF/X-1a writer | General PDF libraries inject clocks, random IDs and encoder drift that break byte-reproducibility |
| HTTP 422 for validation | Standard HTTP semantics; agents must handle 422 to proceed |
| Append-only audit log | Legal defensibility; no mutation of historical records |
| Base64 export data | No file paths cross the trust boundary; data is self-contained |
| Canonical JSON hashing | Platform-independent determinism for manifest verification |
| Mirrored v1 fulfillment contracts | NeuroForge and ForgeImages exchange strict JSON without sharing runtime dependencies |
| Offline candidate validator | Metadata checks are deterministic and testable before durable artifact access exists |
| Self-verifying manifest | Canonical JSON content is bound to a SHA-256 digest and rejects tampering |

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
| GitHub Actions | `ci.yml`: Rust fmt/clippy/test (toolchain 1.97.0), Python tests, documentation parity on every PR. `freeze.yml`: freeze and qualification on ubuntu-22.04, macos-latest, windows-latest |

## Feature Flags

| Flag | Purpose |
|------|---------|
| `test-hooks` | Exposes a `validate_asset()` call counter in `pipeline.rs`. No current test enables it |

---

# §4 — Project Structure

## Directory Tree

```
forgeimages/
├── README.md                          # Overview, Documentation Contract, quick start
├── CLAUDE.md                          # Agent contract: Six Laws, verification, non-obvious rules
├── LICENSE                            # Proprietary, Boswell Digital Solutions LLC
├── Cargo.toml / Cargo.lock            # Workspace (core + tauri); lock is tracked
├── .github/workflows/freeze.yml       # Engine tests + frozen-sidecar build and qualification
│
├── doc/
│   ├── system/                        # Canonical source of truth (this document)
│   │   ├── _index.md                  # Header, truth classes, chapter table
│   │   ├── NN-*.md                    # 18 flat numbered chapters
│   │   ├── system_manifest.json       # Machine section map (bds.repo_doc_system_manifest.v1)
│   │   ├── BUILD.sh                   # Fail-closed assembly
│   │   └── validate_snapshots.sh      # Snapshot and manifest/index validation
│   └── imgSYSTEM.md                   # Generated: assembled reference (do not edit)
│
├── docs/
│   ├── KNOWN_ISSUES.md                # KI-IMG-* findings, root causes, scope
│   ├── forgeimages_architecture_spec.md   # Design intent (subordinate to doc/system/)
│   └── forgeimages_extended_roadmap.md    # Roadmap (subordinate to doc/system/)
│
├── reports/forgeimages-verification/  # Dated evidence: cloud-image Slice 01 and 02
├── files/                             # Pre-implementation design specs (historical)
├── scripts/context-bundle.sh          # AI session context generator
│
├── packaging/                         # Frozen forgeimages-bridge sidecar (§12)
│   ├── build.sh                       # One-commit build: CLI (--locked) + bridge + templates
│   ├── forgeimages-bridge.spec        # PyInstaller spec
│   ├── freeze_entry.py                # Sidecar entry point, --runtime-info, env contract
│   ├── freeze_env.sh                  # Shared CPython 3.12 helper (same as forge-neuronforge)
│   ├── qualify_frozen.py              # Runs and checks the frozen binary
│   └── requirements-freeze.{in,txt}   # Hashed universal lock
│
├── forgeimages-core/                  # Rust engine (v1.0.0, edition 2024)
│   ├── src/
│   │   ├── lib.rs                     # Six Laws, public re-exports, ENGINE_VERSION
│   │   ├── templates.rs               # Template contract types, TemplateRegistry
│   │   ├── validation.rs              # ValidationRule trait, 3 default rules, Validator + failure-mode policy
│   │   ├── rules/                     # Rule library: aspect_ratio, resolution, color_count,
│   │   │                              #   dimensions, color_space, file_size (not in the default Validator)
│   │   ├── pipeline.rs                # CompilationPipeline: validate → master → exports → hashes
│   │   ├── source_master.rs           # Decode, identify, admit and convert a caller's master
│   │   ├── pdf.rs                     # Deterministic raster → PDF/X-1a:2001 writer
│   │   ├── hashing.rs                 # Canonical JSON, SHA-256, job/manifest hashes, provenance types
│   │   ├── print.rs                   # PrintAuthority, PrintSpec, ColorSpace
│   │   ├── cover_params.rs            # Book-cover spine/bleed dimension resolver
│   │   ├── validation_outcome.rs      # ScreenOnly / PrintReady / PrintAdvisory / Draft / Rejected
│   │   ├── file_validation.rs         # Read real dimensions/format from a file (Tauri path)
│   │   └── bin/forgeimages_cli.rs     # CLI: templates, validate, compile; --payload - reads stdin
│   ├── templates/                     # 5 template contracts (§8)
│   └── tests/
│       ├── invariants.rs              # 6 contract invariants
│       ├── source_master.rs           # 19 master ingestion / conversion tests
│       └── cli_payload.rs             # 3 stdin payload tests
│
├── forgeimages-tauri/                 # Tauri 2 IPC commands for AuthorForge (§7)
│   └── src/{lib.rs, commands.rs}
│
└── forgeagents-forgeimages/           # Python package (v1.0.0, Python >=3.10, hatchling)
    ├── bridge/                        # FastAPI bridge + audit + cloud-fulfillment contracts
    ├── skill/                         # ForgeImagesSkill async httpx client
    └── tests/                         # Boundary, CLI payload, cloud-fulfillment tests
```

## Key Module Responsibilities

> Line counts are snapshot facts, counted 2026-10-30.

### Rust Modules (`forgeimages-core/src/`)

| Module | Lines | Responsibility |
|--------|-------|----------------|
| `lib.rs` | 37 | Six Laws docstring, public API re-exports, `ENGINE_VERSION`, `MIN_TEMPLATE_VERSION` |
| `templates.rs` | 196 | `Template`, `AssetClass`, `ValidationConfig`, `FailureMode`, `ExportSpec`, `ExportFormat`, `TemplateRegistry` |
| `validation.rs` | 244 | `ValidationRule` trait, `AspectRatioRule`, `ResolutionRule`, `ColorCountRule`, `Validator` (policy) |
| `rules/` | 407 | Per-rule modules, including `DimensionMatchRule`, `ColorSpaceRule`, `FileSizeRule` for Cover Forge |
| `pipeline.rs` | 317 | `CompilationPipeline`, `CompileRequest`, `CompiledAsset`, `ExportedFile`, `PipelineError` |
| `source_master.rs` | 402 | `decode`, `check_admissible`, `render_export`, `SourceMasterError` |
| `pdf.rs` | 770 | `write_pdf_x1a`, `DeviceColor`, `OutputIntent`, `IccProfile`, `PrintGeometry` |
| `hashing.rs` | 165 | `canonical_json`, `sha256_hex`, `compute_job_hash`, `compute_manifest_hash`, `SourceType`, `AssetManifest` |
| `print.rs` | 80 | `PrintAuthority`, `PrintSpec`, `ColorSpace` |
| `cover_params.rs` | 162 | `CoverTemplateParams`, `PaperStock`, `ResolvedCoverDimensions` |
| `validation_outcome.rs` | 62 | `ValidationOutcome` clearance levels |
| `file_validation.rs` | 54 | `validate_from_file` |
| `bin/forgeimages_cli.rs` | 181 | Clap CLI, exit-code contract |
| `forgeimages-tauri/src/commands.rs` | 96 | 3 Tauri commands, `ForgeImagesState`, `init_state` |

### Python Modules (`forgeagents-forgeimages/`)

| Module | Lines | Responsibility |
|--------|-------|----------------|
| `bridge/forgeimages_bridge.py` | 275 | FastAPI app, 5 endpoints, `call_cli` (payload on stdin), size-limit middleware |
| `bridge/models.py` | 110 | Pydantic v2 models mirroring the Rust types |
| `bridge/audit.py` | 104 | Append-only JSONL audit log with job hash |
| `bridge/settings.py` | 32 | `FORGEIMAGES_*` configuration |
| `bridge/cloud_fulfillment_contracts.py` | 168 | Strict v1 request/result/rejection/compiled-asset records |
| `bridge/cloud_fulfillment_profiles.py` | 118 | Immutable validation profile registry |
| `bridge/cloud_fulfillment_validation.py` | 296 | `DeterministicCloudAssetValidator` |
| `bridge/cloud_fulfillment_manifest.py` | 76 | Self-verifying `ForgeImagesAssetManifestV1` |
| `skill/forgeimages_skill.py` | 377 | `ForgeImagesSkill`, `ForgeImagesError`, result wrappers |

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
| `FORGEIMAGES_MAX_PAYLOAD_SIZE_KB` | int | `512` | Declared but **not enforced**: no code reads it. The request-size middleware uses `MAX_REQUEST_SIZE_MB` only |
| `FORGEIMAGES_ENGINE_VERSION` | str | `"1.0.0"` | Engine version the bridge uses when it computes an audit job hash itself (validate, and compile when the CLI returned none) |

`FORGEIMAGES_BRIDGE_CAPABILITY` is the per-launch caller capability (32–512 URL-safe characters). The bridge refuses every route except `/health` with `503` when it is unset. The AuthorForge shell mints it at each launch.

The frozen sidecar adds `FORGEIMAGES_BRIDGE_HOST` (default `127.0.0.1`; only `127.0.0.1`, `::1` or `localhost`, any other value exits 2) and `FORGEIMAGES_BRIDGE_PORT` (default `8100`). It requires `FORGEIMAGES_AUDIT_LOG_PATH` and exits 2 without it. It defaults the CLI and templates paths to the bundled copies. See §12.

The skill's default bridge URL is `http://127.0.0.1:8100`.

## CLI Flags

### Global Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--templates-dir` | `templates` | Directory containing template JSON files |

### Validate Subcommand

| Flag | Required | Description |
|------|----------|-------------|
| `--template` | Yes | Template ID to validate against |
| `--payload` | Yes | JSON string of AssetInput, or `-` to read it from stdin |

### Compile Subcommand

| Flag | Required | Description |
|------|----------|-------------|
| `--template` | Yes | Template ID to compile against |
| `--payload` | Yes | JSON string of CompileRequest, or `-` to read it from stdin |

## Template Configuration (example: pwa-icon.json)

The five shipped templates are inventoried in §8. The example below shows the contract shape.

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
| 400 | Bad request | `POST /compile/{id}`: the path `template_id` differs from the body's |
| 404 | Not found | `GET /template/{id}` only: template ID not in the CLI's list |
| 413 | Too large | `Content-Length` over `max_request_size_mb` (10 MB) |
| 422 | Validation failure | `/validate`: CLI exit 2. `/compile`: **any** CLI exit 2. That covers rule violations and also an unknown template, a rejected master, or an engine-version mismatch, because the CLI exits 2 for every compile error |
| 422 | Request schema | FastAPI's own body validation (Pydantic), before the CLI runs |
| 500 | Engine error | CLI exit 1 (for example an unknown template on `/validate`), or output that is not JSON |
| 503 | Service unavailable | Rust CLI binary not found |
| 504 | Timeout | CLI execution exceeded 30 seconds |

On `/compile`, read the `detail.error` string to tell a rule violation from a refused master. The status code alone does not distinguish them.

### Middleware

- **Caller boundary** (`bridge/local_caller_boundary.py`, runs first) — Only `GET`/`HEAD /health` is public. Every other route needs a loopback peer address, one loopback `Host` on the bound port, no `Origin`, and the per-launch `X-AuthorForge-ForgeImages-Capability` equal to `FORGEIMAGES_BRIDGE_CAPABILITY`. Every `POST` needs `Content-Type: application/json`. Refusals: `403 invalid_local_caller`, `503 local_capability_unconfigured`, `401 local_capability_required`, `415 application_json_required`. No CLI runs for a refused call. Before a refusal the bridge reads and discards the body, never parsed, for at most 2 s and about 1 MiB; a body that stalls or passes either limit gets the refusal at once with `Connection: close`, and that client may see a reset instead of the status. Ported from forge-cortex (#27, #28, #30).
- **Request size limiter** — Enforces `max_request_size_mb` (default 10 MB)

### Headers

| Header | Direction | Purpose |
|--------|-----------|---------|
| `X-AuthorForge-ForgeImages-Capability` | Request | Per-launch capability; required on every route except `/health`. The agent skill sends it from `FORGEIMAGES_BRIDGE_CAPABILITY`, only to a loopback bridge URL |
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

### Payload on stdin

`--payload -` makes the CLI read the JSON payload from stdin. The bridge always
uses this form for `validate` and `compile`.

The reason is size. A compile payload carries the base64 raster master, which is
often several MiB. Linux refuses a single argument over 128 KiB (`E2BIG`,
"Argument list too long"). Windows limits the whole command line to 32 KiB.
Before this change, every compile of a real diffusion master failed with HTTP 500.

```bash
echo '{"width":1080,"height":1080}' | \
  forgeimages-cli --templates-dir ./templates validate --template panel-square --payload -
```

`forgeimages-core/tests/cli_payload.rs` runs the real binary with a master over
4 MiB. `forgeagents-forgeimages/tests/test_bridge_cli_payload.py` proves that the
bridge puts the payload on stdin and not in the argument list.

### CLI Exit Code Semantics

| Code | Meaning | Bridge Interpretation |
|------|---------|----------------------|
| 0 | Success | HTTP 200 |
| 1 | System error | HTTP 500 |
| 2 | Validation failure | HTTP 422 |

---

# §7 — Tauri Command Interface

`forgeimages-tauri` is a library crate. It holds the Tauri 2 IPC commands that the AuthorForge desktop app registers. It has no `main` and no Tauri app of its own. Nothing in this repository runs these commands. AuthorForge does.

## Registration (in AuthorForge, not here)

AuthorForge vendors this repository as the `third_party/forgeimages` git submodule and depends on the crate by path:

```toml
# AuthorForge src-tauri/Cargo.toml
forgeimages-tauri = { path = "../third_party/forgeimages/forgeimages-tauri" }
```

AuthorForge's `src-tauri/src/main.rs` adds the three commands to its `invoke_handler`. At setup it calls `init_state(resource_dir.join("forgeimages-templates"))` and `app.manage(...)`s the result. The templates AuthorForge bundles are its own copies under `src-tauri/forgeimages-templates/`, **not** this repository's `forgeimages-core/templates/`. The two sets can drift. Check both when you change a template (§17).

## Managed State

```rust
pub struct ForgeImagesState {
    pub pipeline: Mutex<CompilationPipeline>,
}

pub fn init_state(templates_dir: PathBuf) -> ForgeImagesState
```

`init_state` loads the template directory with `TemplateRegistry::load_from_dir`. If loading fails, it falls back to an **empty** registry and does not raise. A missing or unreadable templates directory therefore produces a working app where every command reports `Template not found`. It does not fail at startup.

Each command takes the mutex. A poisoned lock returns the error string `"Lock poisoned"`.

## Commands

| Command | Arguments | Returns | Engine call |
| --- | --- | --- | --- |
| `forgeimages_list_templates` | none | `Vec<TemplateInfo>` | `list_templates()` |
| `forgeimages_validate_file` | `asset_path: String`, `template_id: String` | `ValidationResult` | `validate_from_file(path)` then `validate_asset()` |
| `forgeimages_validate_metadata` | `input: AssetInput`, `template_id: String` | `ValidationResult` | `validate_asset()` |

`TemplateInfo` is `{ id, name, version, asset_class, deprecated }`. `asset_class` is the `Debug` form lower-cased (for example `characterportrait`). That differs from the serde form the CLI emits (`character_portrait`). A frontend that compares the two will not match multi-word classes.

All errors cross IPC as `Err(String)`, the `Display` form of the underlying `PipelineError` or `FileValidationError`.

### `forgeimages_validate_file`

This command reads the real file, decodes it with the `image` crate (JPEG, PNG and TIFF are enabled), and validates the actual pixel dimensions. Declared metadata plays no part. `color_count` is always `None` on this path, so the colour-count rule never fires for file validation. The command decodes the whole image to learn its size, so memory use grows with the image.

## What the Desktop Path Does Not Do

- **No compile.** There is no Tauri command for `compile_asset`. Desktop compilation, if AuthorForge needs it, goes through the `forgeimages-bridge` sidecar (§12).
- **No audit log.** The audit log is written by the Python bridge. Tauri validations are not logged by ForgeImages.
- **No `ValidationOutcome`.** The commands return the raw `ValidationResult`. AuthorForge derives any clearance level itself.

---

# §8 — Backend Internals

## Template System (`templates.rs`)

### Core Types

**Template** — The contract definition:
- `id: TemplateId` — Unique identifier (e.g., "pwa-icon")
- `name: String` — Human-readable name
- `template_version: Version` — Semver version
- `engine_min_version: Version` — Minimum compatible engine
- `asset_class: AssetClass` — see below
- `aspect_ratio: (u32, u32)` — Expected ratio
- `canonical_size: (u32, u32)` — Ideal dimensions
- `vector_master: bool` — Whether SVG master is required
- `validation: ValidationConfig` — Rules and failure mode
- `exports: Vec<ExportSpec>` — Output specifications

**AssetClass enum** — `icon | cover | banner | logo | map | panel | character_portrait | scene_illustration | marketing_social` (the last five were added for AuthorForge)

**FailureMode enum** — Determines what happens when validation finds errors:
- `Block` (default) — Errors prevent compilation
- `Warn` — Errors recorded, `valid: true`, compilation proceeds
- `Log` — Same result as `Warn` in the current engine. `Validator::validate` handles `Warn | Log` in one arm, so the two modes are indistinguishable in output today

**TemplateRegistry** — HashMap-backed registry:
- `load_from_dir(path)` — Loads all `.json` files from directory. A file that cannot be read or does not parse as a `Template` is **skipped silently**: no error, no log. A typo in a template JSON shows up only as `Template not found` later
- `get(id)` — Retrieve template by ID
- `list()` — List all registered templates
- `register(template)` — Add a template to the registry

### Shipped Templates

> Snapshot fact, read from `forgeimages-core/templates/` on 2026-10-30.

| ID | Class | Version | Ratio | Canonical size | Vector master | Failure mode | Exports (required marked \*) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `pwa-icon` | icon | 1.0.0 | 1:1 | 1024×1024 | yes | block | `master` svg\*, `favicon-16`/`favicon-32`/`apple-touch`/`pwa-192`/`pwa-512` png\* |
| `book-cover-kdp` | cover | 2.0.0 | 13:9 | 3896×2775 | no | block | `cover-pdf` pdf 3896×2775\*, `cover-preview` jpg 1200×855 |
| `panel-square` | panel | 2.0.0 | 1:1 | 1080×1080 | no | warn | `panel-square-png` png\*, `panel-square-preview` jpg 270×270 |
| `panel-fullhd` | panel | 2.0.0 | 16:9 | 1920×1080 | no | warn | `panel-fullhd-png` png\*, `panel-fullhd-preview` jpg 480×270 |
| `panel-4k` | panel | 2.0.0 | 16:9 | 3840×2160 | no | warn | `panel-4k-png` png\*, `panel-4k-preview` jpg 960×540 |

`pwa-icon` requires a vector master, and this engine has no SVG rasterizer. With an SVG master, its PNG exports are refused (`UnsupportedConversion`). Without a master, it compiles to placeholders. It cannot yet produce a real icon set (§14).

The `required` flag on an `ExportSpec` is carried in the contract, but the pipeline does not branch on it. Every export in the list is produced, or the compile fails.

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

### Rule Library vs Default Rules

`Validator::new()` wires exactly three rules, defined in `validation.rs`: `AspectRatioRule`, `ResolutionRule`, `ColorCountRule`. Those are the only rules the CLI, the bridge and the Tauri commands run.

`rules/` also holds `DimensionMatchRule` (exact size ±2 px), `ColorSpaceRule` (`cmyk_required()` is advisory), and `FileSizeRule` (`kdp()` 650 MB, `ingram_spark()` 600 MB). They implement `ValidationRule` and can be added with `Validator::add_rule`, but **no caller in this repository adds them**. The same holds for `CoverTemplateParams` (spine width from page count and paper stock), `ValidationOutcome` and `PrintSpec`. They are public library API, exported from `lib.rs`, and are not on any served path yet (§14).

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
2. **Validate asset** — `validate_asset()`: engine-version check, then the 3 rules and the failure mode
3. **Reject on failure** — `valid: false` returns `ValidationFailed` with the joined violation messages
4. **Ingest the master** — if `source_data` is present: `source_master::decode` then `check_admissible` (vector-master requirement, declared vs real dimensions). Any failure is `SourceMasterRejected`
5. **Generate exports** — one `ExportedFile` per `ExportSpec`. With a master: `source_master::render_export`, which fails the compile on any conversion it cannot honour. Without a master: placeholders (an empty `<svg>`, a 1×1 PNG, or the bytes `placeholder` for every other format)
6. **Compute hashes** — `job_hash` over template id, template version, the canonical request and the engine version; then `manifest_hash` over the whole `CompiledAsset`
7. **Return CompiledAsset**

`CompiledAsset.id` is a fresh UUIDv4 and `created_at` is the wall clock, and both are inside the hashed manifest. So `manifest_hash` differs on every compile, even for identical input. Reproducibility is carried by `job_hash` and by each export's `hash`, which are stable (Law 4).

## Source Master Ingestion (`source_master.rs`)

`decode` base64-decodes `source_data` and identifies it. Text starting `<svg`, or `<?xml` containing `<svg`, after an optional BOM, is SVG. Anything the `image` crate can decode is a raster, and its real dimensions are recorded. Empty, undecodable or unrecognised input is an error. It is never treated as "no master supplied".

`check_admissible` refuses a raster master for a `vectorMaster: true` template. It also refuses any raster whose real dimensions differ from the `asset_input` the validator approved.

`render_export` conversion matrix:

| Master → export | Result |
| --- | --- |
| SVG → SVG | Pass-through bytes |
| raster → PNG / JPG | Pass-through when format and size already match, otherwise a Lanczos3 resize and re-encode (deterministic) |
| raster → PDF | PDF/X-1a:2001 via `pdf.rs`, only for opaque 8-bit grayscale. RGB is refused (`PrintColorNotAdmissible`), alpha is refused (`PrintTransparencyNotAllowed`) |
| SVG → anything else | Refused: no rasterizer |
| raster → SVG, any → ICO | Refused |

The PDF path uses a fixed 300 DPI and a 0.125" KDP bleed for the `TrimBox` (constants in `source_master.rs`), with `OutputIntent::kdp_us_swop()`.

### Three Validation Rules

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

# §9 — Ecosystem Integration

## Integration Map

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  VibeForge   │     │ ForgeAgents  │     │ AuthorForge  │
│ (not wired)  │     │ (orch.)      │     │ (active)     │
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

## AuthorForge Integration (Active)

AuthorForge is the shipping consumer. It vendors this repository as the `third_party/forgeimages` submodule (`git@github.com:Boswell-Digital-Solutions/forgeimages.git`) and uses it two ways:

| Surface | What AuthorForge uses | Chapter |
| --- | --- | --- |
| Desktop validation | `forgeimages-tauri` commands, registered in AuthorForge `src-tauri/src/main.rs`, with templates bundled from AuthorForge's own `src-tauri/forgeimages-templates/` | §7 |
| Image-generation lane | The frozen `forgeimages-bridge` sidecar in release bundles. NeuronForge Local sends every diffusion master to it at `FORGEIMAGES_URL` (port 8100) | §12 |

AuthorForge owns its submodule pin. A change here reaches AuthorForge only when AuthorForge bumps `third_party/forgeimages` (§17).

## VibeForge Integration (Not Implemented)

Earlier plans named VibeForge as the primary consumer, through Tauri commands. No VibeForge code consumes ForgeImages. The Tauri crate that exists (§7) was built for AuthorForge. Treat VibeForge integration as unscheduled.

## NeuroForge Cloud Fulfillment (Contracts Only)

NeuroForge owns cloud generation and the fulfillment saga. ForgeImages owns deterministic validation. The bridge package carries the v1 request/result contracts, the profile registry, the offline `DeterministicCloudAssetValidator` and the self-verifying manifest (§6, §8). **No HTTP route serves them.** No artifact-byte retrieval, durable manifest store or replacement loop exists. Evidence for Slices 01 and 02 is under `reports/forgeimages-verification/`.

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
| Input | JSON on stdin via `--payload -` (always, for validate and compile) |
| Output | JSON on stdout |
| Exit 0 | Success |
| Exit 2 | Validation/compilation failure |
| Exit 1 | System error |
| Timeout | 30 seconds |

---

# §10 — Error Handling

## The 422 Contract

HTTP 422 (Unprocessable Entity) is the enforcement mechanism. When the CLI exits `2`, the bridge raises `HTTPException(422)`. An agent cannot proceed past it.

```
Agent → POST /validate/pwa-icon → Bridge → CLI validate (stdin) → exit 2
Agent ← 422 {detail: {...}}     ← Bridge (audit line written first)
```

The 422 body is FastAPI's `{"detail": ...}` wrapper, not a bare `ValidationResult`:

| Endpoint | `detail` on exit 2 |
| --- | --- |
| `POST /validate/{id}` | `{"message": "Validation failed", "violations": [...], "template_id", "template_version"}` |
| `POST /compile/{id}` | `{"message": "Compilation failed", "error": "<PipelineError text>", "template_id"}`. There is no `violations` array. Rule messages are joined into `error` |

FastAPI also returns 422 when the request body fails Pydantic validation. That body is a `detail` list of field errors, and it is produced before the CLI runs.

## Rust Error Types (`pipeline.rs`)

```rust
pub enum PipelineError {
    #[error("Template not found: {0}")]
    TemplateNotFound(String),
    #[error("Validation failed: {0}")]
    ValidationFailed(String),               // "rule: message; rule: message"
    #[error("Template version {0} requires engine >= {1}, current is {2}")]
    EngineVersionMismatch(String, String, String),
    #[error("Compilation error: {0}")]
    CompilationError(String),
    #[error("Serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),
    #[error("Source master rejected: {0}")]
    SourceMasterRejected(#[from] SourceMasterError),
}
```

`SourceMasterError` (`source_master.rs`) names the exact refusal: `InvalidBase64`, `Empty`, `UnrecognizedFormat`, `RasterDecode`, `VectorMasterRequired`, `DeclaredDimensionMismatch`, `UnsupportedConversion`, `EncodeFailed`, `PrintColorNotAdmissible`, `PrintTransparencyNotAllowed`, `PdfWriteFailed`. Every one fails the whole compile. None degrades to a placeholder.

Other error enums: `FileValidationError` (`FileNotFound`, `ReadError`, `DecodeError`) on the Tauri path, and `PdfError` inside the PDF writer.

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

| Code | `validate` | `compile` | Bridge action |
|------|-----------|-----------|---------------|
| 0 | Result with `valid: true` (warnings allowed) | `{"success": true, "asset": ...}` | 200 |
| 1 | Unreadable payload, invalid JSON, unknown template, engine-version mismatch | Unreadable payload or invalid JSON | 500 |
| 2 | Result with `valid: false` | **Any** `PipelineError`: rule failure, unknown template, version mismatch, rejected master, serialization | 422 |

Template-directory load failure exits 1 before any subcommand runs. Errors on stdout are JSON objects with an `error` field.

The asymmetry is deliberate in effect, though not documented as intent in the code. `compile` maps every engine error to 2, so an agent can never treat a failed compile as a system fault and retry around it. The cost is that the 422 alone does not tell a rule failure from a refused master. Read `detail.error`.

## Bridge Error Responses

| HTTP Status | Condition | Response Body |
|-------------|-----------|---------------|
| 400 | Path and body `template_id` differ on `/compile` | `{"detail": "template_id in path must match request body"}` |
| 404 | `GET /template/{id}` not found | `{"detail": "Template not found: {id}"}` |
| 413 | Body over 10 MB | `{"detail": "Request too large"}` |
| 422 | CLI exit 2 | See the 422 contract above |
| 500 | CLI exit 1, or non-JSON output | `{"detail": "<CLI error>"}`, or `"Invalid CLI output"` |
| 503 | CLI binary not found | `{"detail": "ForgeImages CLI not found. Build with: cargo build --release"}` |
| 504 | CLI exceeded 30 s | `{"detail": "ForgeImages CLI timeout"}` |

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
| Template ID format | `CompileRequest.template_id` (body) | `^[a-z0-9][a-z0-9-]*$`, 1–64 characters |
| Prompt length | prompt | Max 2000 characters |
| Seed value | seed | Non-negative integer |

Invalid input is rejected at the Pydantic layer before the CLI is ever invoked.

The **path** `{template_id}` is not pattern-checked on any endpoint. It goes to the CLI as one argv element (`subprocess.run` with a list, no shell), and the engine uses it only as a registry lookup key, so it cannot inject a command or reach the filesystem. An unknown ID simply fails the lookup.

---

# §11 — Testing

## Test Suite Overview

> Snapshot fact: counts and results from a run on 2026-10-30 (Windows 11, stable Rust, Python 3.12). Recount before relying on them.

| Layer | Tests | File | Framework |
|-------|-------|------|-----------|
| Rust invariants | 6 | `forgeimages-core/tests/invariants.rs` | cargo test |
| Rust source-master ingestion | 19 | `forgeimages-core/tests/source_master.rs` | cargo test |
| Rust CLI stdin payload | 3 | `forgeimages-core/tests/cli_payload.rs` | cargo test |
| Rust inline unit tests | 23 | `pdf.rs` (14), `hashing.rs` (3), `cover_params.rs` (3), `rules/dimensions.rs` (3) | cargo test |
| Python agent boundaries | 18 | `tests/test_agent_boundary.py` | pytest |
| Python bridge stdin payload | 2 | `tests/test_bridge_cli_payload.py` | pytest |
| Cloud validation contracts | 18 | `test_forgeimages_validation_contracts.py` (13), `test_forgeimages_rejection_report_contract.py` (5) | pytest |
| Cloud validator and manifests | 14 | `test_forgeimages_asset_validator.py` (10), `test_forgeimages_asset_manifest.py` (4) | pytest |
| **Total** | **51 Rust, 52 Python** | all passing | |

`forgeimages-tauri` has no tests. The three commands are thin wrappers over engine calls the tests above cover, but their state handling (empty-registry fallback, lock poisoning) is unexercised. The `test-hooks` feature (a validation-call counter in `pipeline.rs`) is not used by any current test. `invariant_compile_calls_validate` proves the invariant by rejecting an invalid asset at compile time. CI runs both suites (see Continuous Integration below).

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

### Rust Inline Tests (hashing.rs; pdf.rs, cover_params.rs and rules/dimensions.rs carry their own)

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

## Continuous Integration

`.github/workflows/ci.yml` runs on every pull request to `master` and every push to `master`. It has three jobs:

| Job | Commands | Notes |
|-----|----------|-------|
| Rust | `cargo fmt --all -- --check`, `cargo clippy --locked --workspace --all-targets -- -D warnings`, `cargo test --locked --workspace` | Toolchain pinned to 1.97.0. Installs GTK and WebKitGTK, because `forgeimages-tauri` links Tauri. |
| Python | `pytest tests/ -q` in `forgeagents-forgeimages` | Python 3.12. Runtime dependencies come from the hashed `packaging/requirements-freeze.txt`. |
| Documentation | `bash doc/system/BUILD.sh`, then `git diff --exit-code -- doc/` | Fails when `doc/imgSYSTEM.md` differs from its parts. |

`.github/workflows/freeze.yml` is separate. It freezes and runs the sidecar on Linux, macOS, and Windows, and runs only when packaging or engine paths change.

A workflow that exists is not a required check. Making `CI` a required status check is a separate repository-settings decision.

## Test Philosophy

1. **Invariant tests verify laws, not features.** Each test maps to one of the Six Laws.
2. **Boundary tests verify trust boundaries.** Each test verifies that agents cannot bypass enforcement.
3. **No mocks of the core engine.** Bridge tests may mock the CLI subprocess, but invariant tests use the real pipeline.
4. **Exit code 2 is sacred.** Tests verify that validation failures always produce exit code 2, never exit code 1 or 0.

---

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

The bridge requires the per-launch capability in `FORGEIMAGES_BRIDGE_CAPABILITY` on every route except `/health`, and refuses a non-loopback peer, `Host` or bind (KI-IMG-20261030-001; see §6 Middleware).

## Qualification

`packaging/qualify_frozen.py` runs the binary and checks the runtime report, the
refusals, `/health`, four caller-boundary refusals (no capability, wrong
capability, `Origin`, rebound `Host`) with no audit line, `/templates`, a compile of a 1080×1080 noise master of more
than 4 MiB, the audit line, and the teardown. `.github/workflows/freeze.yml` runs
the engine tests, the build and the qualification on ubuntu-22.04, macos-latest
and windows-latest.

---

# §13 — Handover

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

- [x] Core Rust library (`forgeimages-core` v1.0.0) and CLI (`templates`, `validate`, `compile`, `--payload -`)
- [x] Template system with 5 shipped contracts (§8)
- [x] Validation pipeline (3 default rules and the failure-mode policy)
- [x] SHA-256 job, manifest and export hashes over canonical JSON
- [x] Compilation that always validates first
- [x] Source-master ingestion: SVG pass-through, raster PNG/JPEG resize, refusal of everything else by name
- [x] Deterministic raster → PDF/X-1a:2001 writer for opaque grayscale masters
- [x] Bridge service (5 FastAPI endpoints, payload on stdin, append-only audit log)
- [x] Skill wrapper (async httpx client, default `http://127.0.0.1:8100`)
- [x] Tauri commands for AuthorForge (§7)
- [x] Frozen `forgeimages-bridge` sidecar, qualified on three OSes in CI (§12)
- [x] Cloud-fulfillment Slice 01 contracts and Slice 02 offline validator and manifest
- [ ] Served cloud-fulfillment route, artifact-byte retrieval, durable manifest store, replacement loop (Slice 03 is next)
- [ ] SVG rasterization, ICO export, RGB→CMYK print path (§14)

Gaps and deferred work are tallied in §14.

## Adding a New Template

1. Create a JSON file in `forgeimages-core/templates/` following an existing template's structure. A new ID, or a bumped `templateVersion` for a behaviour change: never edit a published template in place
2. Set `templateVersion` to "1.0.0" and `engineMinVersion` to the current engine version
3. Define validation rules (aspect ratio, resolution, color count)
4. Define export specifications (format, size, required flag)
5. Run `cargo test`, then check that the CLI actually lists it (`forgeimages-cli --templates-dir forgeimages-core/templates templates`). The registry skips an unparseable file silently, so a passing test run does not prove the template loaded
6. If AuthorForge needs it on the desktop path, also add it to AuthorForge's `src-tauri/forgeimages-templates/`
7. Test via CLI: `forgeimages-cli validate --template <id> --payload '...'`

## Adding a New Validation Rule

1. Define a struct implementing the `ValidationRule` trait in `validation.rs`
2. Implement `name()` and `validate()` methods
3. Add the rule to the `Validator` struct's rule list
4. Add invariant tests in `tests/invariants.rs`
5. Add boundary tests in `tests/test_agent_boundary.py`
6. Update this documentation (§8 and §11) and `system_manifest.json` if a chapter is added

---

# §14 — Known Gaps & Future-Work Tally

This chapter lists what the code does **not** do yet, or does in a way a reader could mistake for more than it is. Each entry was checked against source on 2026-10-30. Formal defect records live in `docs/KNOWN_ISSUES.md` (`KI-IMG-*`). An entry here is not a KI unless it says so.

## Output Fidelity

| # | Gap | Where | Effect |
| --- | --- | --- | --- |
| G1 | A compile **without** `source_data` returns placeholder exports: an empty `<svg>`, a 1×1 PNG, or the literal bytes `placeholder` for JPG/PDF/ICO | `pipeline.rs` `render_export` | The response reports `success: true` with real hashes. For `book-cover-kdp`, the `required` `cover-pdf` is the bytes `placeholder`. Callers must supply a master to get real files |
| G2 | No SVG rasterizer | `source_master.rs` | An SVG master produces only SVG exports. `pwa-icon` (vector master required, five PNG exports) cannot produce a real icon set. The separate `Forge_Images` repository has a `resvg`-based renderer that has not been ported here |
| G3 | ICO export is refused from every master | `source_master.rs` | No template ships an ICO export today, so nothing breaks yet |
| G4 | PDF/X-1a is admitted only from opaque 8-bit grayscale masters | `source_master.rs` | RGB masters are refused by design (no colour-managed RGB→CMYK). The writer can represent CMYK, but no ingest path accepts a CMYK master yet. A colour book cover cannot compile to print |
| G5 | The PDF output intent is named, not embedded (`kdp_us_swop`) | `pdf.rs` | Structurally PDF/X-1a:2001. Strict vendor preflight may want an embedded ICC profile. Not verified against a real RIP |

## Validation Coverage

| # | Gap | Where | Effect |
| --- | --- | --- | --- |
| G6 | `DimensionMatchRule`, `ColorSpaceRule`, `FileSizeRule`, `CoverTemplateParams`, `ValidationOutcome` and `PrintSpec` are public API that no caller wires in | `rules/`, `cover_params.rs`, `validation_outcome.rs`, `print.rs` | `book-cover-kdp` is validated on aspect ratio and minimum resolution only. Spine width, exact trim size, colour space and file size are not checked on any served path |
| G7 | `FailureMode::Log` behaves exactly like `Warn` | `validation.rs` | The two modes cannot be told apart in output |
| G8 | `TemplateRegistry::load_from_dir` skips unreadable or unparseable files silently | `templates.rs` | A broken template surfaces later as `Template not found`, with no load-time error |
| G9 | The colour-count rule never runs on the Tauri file path | `file_validation.rs` | `color_count` is always `None` there |

## Bridge and Interfaces

| # | Gap | Where | Effect |
| --- | --- | --- | --- |
| G0 | Closed. The bridge admitted any local caller, including a browser page via DNS rebinding. The caller boundary is merged (`f308cdd`, #13): loopback peer and `Host`, no `Origin`, the per-launch capability. AuthorForge pins it and proves its real image path in the release smoke (Author-Forge #934, #935) | `bridge/local_caller_boundary.py` | **KI-IMG-20261030-001 (closed).** |
| G10 | `/compile` returns 422 for every engine error | CLI + bridge | A rule failure, an unknown template and a refused master share one status. Distinguish them by `detail.error` |
| G11 | `FORGEIMAGES_MAX_PAYLOAD_SIZE_KB` is declared and never read | `settings.py` | Only the 10 MB request limit applies |
| G12 | The validate audit `job_hash` uses the bridge's configured `engine_version`, not the CLI's | `forgeimages_bridge.py` | If the two diverge, the audit hash names the wrong engine |
| G13 | Tauri `TemplateInfo.asset_class` uses the `Debug` form (`characterportrait`), and the CLI uses the serde form (`character_portrait`) | `forgeimages-tauri/src/commands.rs` | Multi-word classes do not match across the two paths |
| G14 | Cloud-fulfillment contracts, profiles, validator and manifest are not served | `bridge/cloud_fulfillment_*` | Slice 03 (replacement feedback, initially with stubs and mocks) is the next governed step |
| G15 | `Settings` uses Pydantic's class-based `Config` | `settings.py` | A deprecation warning on every test run; it breaks in Pydantic v3 |

## Verification and Delivery

| # | Gap | Where | Effect |
| --- | --- | --- | --- |
| G16 | `CI` (`ci.yml`) runs on every PR but is not a required status check | repository settings | A red run does not block a merge |
| G17 | `freeze.yml` is path-filtered to `packaging/`, `bridge/`, `forgeimages-core/` and the Cargo files | `freeze.yml` | Sidecar qualification does not run for other changes. `ci.yml` covers the tests |
| G18 | `forgeimages-tauri` has no tests | `forgeimages-tauri/` | The empty-registry fallback and lock handling are unexercised |
| G19 | AuthorForge bundles its own copies of the templates | AuthorForge `src-tauri/forgeimages-templates/` | The desktop path and the sidecar path can validate against different contract versions |

## Not Planned Here

- **Image generation.** It belongs to NeuronForge Local and NeuroForge.
- **Colour-managed conversion.** ForgeImages refuses instead of inventing colour. A conversion step would be a deliberate new capability with its own profile authority.
- **VibeForge integration.** Unscheduled. No consumer exists (§9).
- **MCP tool definitions.** Proposed in earlier plans. No work has started.

---

# §15 — Scope

## What This Document Covers

This `doc/system/` tree is the canonical technical reference for the `forgeimages` repository (designation `img`, git remote `Boswell-Digital-Solutions/forgeimages`). It covers:

- the Rust engine `forgeimages-core`, its CLI, and its template contracts
- the Tauri command crate `forgeimages-tauri`
- the Python package `forgeagents-forgeimages`: bridge, skill and cloud-fulfillment contracts
- the frozen `forgeimages-bridge` sidecar build under `packaging/`, and its CI qualification

## What It Does Not Cover

| Out of scope | Owner |
| --- | --- |
| The separate `Forge_Images` repository (underscore, designation `ima`) | That repository's own `doc/system/` |
| How AuthorForge registers, bundles and launches ForgeImages | AuthorForge `doc/system/` |
| Image generation and the cloud fulfillment saga | NeuronForge Local, NeuroForge |
| Persistence of compiled assets and their metadata | The calling system (DataForge is the ecosystem record store) |
| Fleet documentation protocol, designation registry, doc audits | The forge meta-repo (`doc/BDS_DOCUMENTATION_PROTOCOL_v2.md`, `doc/PREFIX_REGISTRY.md`) |

## Truth Classes

Every statement in this document is one of two classes. `_index.md` declares them.

- **Canonical facts** define role, the Six Laws, authority boundaries, contracts (exit codes, HTTP status mapping, the template schema, the payload-on-stdin rule) and invariants. They change only through §17 and are expected to stay true between audits.
- **Snapshot facts** are dated counts and inventories: file and line counts, test counts and results, the shipped-template table, the gap tally. Each is marked with the date it was taken. They drift as code lands. Recount before relying on one.

## Authority Order

When sources disagree, resolve in this order:

1. **Code and tests** in this repository at the commit in question.
2. **This `doc/system/` tree** and its compiled `doc/imgSYSTEM.md`.
3. `CLAUDE.md` (agent contract) and `README.md` (overview).
4. `docs/forgeimages_architecture_spec.md`, `docs/forgeimages_extended_roadmap.md`, and the historical specs under `files/`. These record intent. They do not override implemented reality.

A disagreement between (1) and (2) is a documentation defect. Fix the chapter (§17). Do not cite the chapter against the code.

---

# §16 — Governance

## Ownership

ForgeImages is owned and operated by Boswell Digital Solutions LLC (proprietary licence, see `LICENSE`). There is a single owner and operator. Every change merges through a pull request to `master` on `Boswell-Digital-Solutions/forgeimages`.

## Designation

| Item | Value |
| --- | --- |
| Designation | `img` |
| Compiled artifact | `doc/imgSYSTEM.md` |
| Registry | forge meta-repo `doc/PREFIX_REGISTRY.md` |
| History | `ima` until 2026-09-24, when the operator resolved a collision with `Forge_Images` (which kept `ima`). The repo emitted the uppercase `IMGSYSTEM.md` until this canonicalization moved it to the lowercase standard the registry records |

The designation appears in exactly four places: `_index.md`, `BUILD.sh` (`DESIGNATION="img"`), `validate_snapshots.sh`, and `system_manifest.json`. A change to it is a registry change first. Update `PREFIX_REGISTRY.md` in the forge meta-repo, then all four files here in one commit.

## Authority Boundaries

| ForgeImages decides | ForgeImages does not decide |
| --- | --- |
| Whether an asset satisfies a template | What image to generate, or which provider generates it |
| Which conversions it will perform, and refusing the rest | Colour management (RGB→CMYK) |
| The template contract schema and the shipped templates | Which ForgeImages commit AuthorForge ships (AuthorForge's submodule pin) |
| The CLI exit-code and bridge HTTP-status contracts | Where compiled assets are stored |

## Change Authority by Surface

| Surface | Rule |
| --- | --- |
| The Six Laws, `compile_asset` → `validate_asset`, CLI exit code `2`, HTTP 422 on exit 2, the append-only audit log | Invariants. A change needs an explicit operator decision recorded in the PR, plus the matching invariant or boundary test change |
| A published template (`id` + `templateVersion`) | Immutable. Ship a new version instead (Law 2) |
| Cloud-fulfillment `*.v1` schemas and rejection codes | Versioned contracts mirrored by NeuroForge. Additive changes need a new schema version, coordinated with NeuroForge |
| Sidecar runtime contract (env vars, port 8100, `--runtime-info`) | Consumed by AuthorForge and NeuronForge Local. Coordinate before changing |
| `Cargo.lock`, `packaging/requirements-freeze.txt` | Regenerate only with the documented commands. Never hand-edit |

---

# §17 — Change Control

## Workflow

1. Branch from current `origin/master`.
2. Make the change. Edit chapters under `doc/system/` in the same PR when the change touches anything a chapter describes (see the triggers below).
3. Run the verification set:

   ```bash
   cargo fmt --all -- --check
   cargo clippy --locked --workspace --all-targets -- -D warnings
   cargo test --locked --workspace
   cd forgeagents-forgeimages && pytest tests/ -q
   bash doc/system/BUILD.sh        # must print BUILD_OK
   ```

4. Commit `doc/imgSYSTEM.md` together with its sources. The compiled file is tracked so that a PR diff shows the documentation change.
5. Open the PR. `ci.yml` runs the same Rust and Python commands and the documentation parity check (`BUILD.sh`, then `git diff --exit-code -- doc/`) on every PR. `freeze.yml` additionally freezes and qualifies the sidecar when packaging or engine paths change. `CI` is not yet a required status check.

## Documentation Maintenance Triggers

`system_manifest.json` maps each chapter to the surfaces it owns and the events that make it stale. The common ones:

| When you change… | Update |
| --- | --- |
| A bridge endpoint, a status mapping, a model field | §6, §10 |
| A Tauri command or `init_state` | §7 |
| Engine modules, conversion rules, the PDF writer | §8, §14 |
| A template file | §8 (shipped-template table), and tell AuthorForge to sync its copy |
| CLI flags or exit codes | §5, §6, §10 |
| A dependency, the Rust edition, the Python floor, the freeze lock | §3 |
| A test file, or test counts | §11 |
| `packaging/` or `freeze.yml` | §12, §3 |
| A gap closed or found | §14, and `docs/KNOWN_ISSUES.md` when it is a defect |

## Defect Records

A defect found in this repository is recorded in `docs/KNOWN_ISSUES.md` as `KI-IMG-YYYYMMDD-NNN`, with date, what is wrong, root cause, fix and scope (open or closed). A defect is closed by the PR that fixes it, and the entry names that change.

## Reaching Consumers

AuthorForge pins this repository as a submodule. A merge here changes nothing in AuthorForge until AuthorForge bumps `third_party/forgeimages` in its own PR. That PR is where a change to the Tauri commands, the sidecar contract or a template reaches users. For templates, AuthorForge also has to copy the file into `src-tauri/forgeimages-templates/`.

## Doc-System Rules

- Chapters are flat `NN-kebab-case.md` files directly under `doc/system/`. `BUILD.sh` fails on any subdirectory or symlink.
- Every chapter appears once in the `_index.md` table and once in `system_manifest.json`. `validate_snapshots.sh` fails the build if the three sets disagree.
- Never hand-edit `doc/imgSYSTEM.md`. Rebuild it.
- Number `00` is reserved. Leave gaps rather than renumbering published chapters without a reason.

---

# §18 — Appendices

## Glossary

| Term | Meaning |
| --- | --- |
| Master | The caller-supplied source asset in `CompileRequest.source_data` (base64), either SVG or a decodable raster |
| Vector master | A template flag (`vectorMaster`). When true, a raster master is refused (Law 1) |
| Placeholder export | The stand-in bytes the pipeline emits when **no** master is supplied (§14 G1) |
| Template contract | A versioned JSON file defining ratio, size, rules, failure mode and exports. Immutable once published |
| Failure mode | `block`, `warn` or `log`. The policy the `Validator` applies to rule violations |
| Job hash | SHA-256 of `template_id:template_version:canonical_request:engine_version`. Stable for identical input |
| Manifest hash | SHA-256 of the canonical `CompiledAsset`. Includes a fresh UUID and timestamp, so it is unique per compile |
| Canonical JSON | Sorted keys, no whitespace. The only form that is ever hashed |
| PDF/X-1a | ISO print-exchange standard: device grayscale/CMYK only, no transparency, an output intent and a `TrimBox` |
| Output intent | The printing condition a PDF/X file declares (`kdp_us_swop` by default, referenced by name) |
| Sidecar | The frozen `forgeimages-bridge` binary that AuthorForge release bundles run on port 8100 |
| Slice 01 / 02 / 03 | Phases of the NeuroForge cloud-image fulfillment boundary: contracts; offline validator and manifest; replacement feedback (next) |

## Cross-References

| Document | Role |
| --- | --- |
| `README.md` | Overview, Documentation Contract, quick start |
| `CLAUDE.md` | Agent contract: laws, verification commands, non-obvious rules |
| `docs/KNOWN_ISSUES.md` | `KI-IMG-*` defect records |
| `docs/forgeimages_architecture_spec.md`, `docs/forgeimages_extended_roadmap.md` | Design intent and roadmap (subordinate to this document, §15) |
| `reports/forgeimages-verification/cloud-image-slice-0{1,2}.md` | Dated evidence for the cloud-fulfillment slices |
| `files/step*.md` | Pre-implementation design specs (historical) |
| forge meta-repo `doc/BDS_DOCUMENTATION_PROTOCOL_v2.md` | The documentation protocol this tree follows |
| forge meta-repo `doc/PREFIX_REGISTRY.md` | Designation registry (`img`) |
| `Forge_Command/doc/system/` | Reference implementation of the canonical doc-system shape |

## Revision History

| Version | Date | Change |
| --- | --- | --- |
| 3.0 | 2026-10-30 | Canonicalized to the Forge_Command shape. Duplicate chapters removed (`91-bootstrap-overview`, `92-bootstrap-architecture`, `20-structure`) and the double `10-` numbering resolved. Chapters renumbered 01–18 in order, with headings matching file numbers. Bootstrap stubs for scope, governance and change control replaced with authored content. Added §7 Tauri Command Interface and §14 Known Gaps. Corrected stale facts against the code: AuthorForge is active rather than "future", the error enum and 422 body shape, exit-code mapping, test counts, asset classes, the shipped-template inventory. Designation lowercased `IMG` → `img` to match `PREFIX_REGISTRY.md`. Output renamed to `doc/imgSYSTEM.md`, and stale `SYSTEM.md`, `doc/SYSTEM.md` and `doc/fiSYSTEM.md` removed. Added `system_manifest.json` and manifest/index alignment checks |
| 2.0 | 2026-06-22 | Canonical compliance migration (designation markers, fail-closed build); later flattened off the numbered-subdirectory layout (PR #8) |
| 1.0 | — | Bootstrap scaffold generated by Forge_Command registry remediation |

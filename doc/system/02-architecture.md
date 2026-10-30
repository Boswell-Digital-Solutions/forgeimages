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

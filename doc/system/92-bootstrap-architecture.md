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

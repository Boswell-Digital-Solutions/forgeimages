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

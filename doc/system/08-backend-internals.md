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

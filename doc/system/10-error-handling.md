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

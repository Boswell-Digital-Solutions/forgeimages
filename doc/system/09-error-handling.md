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

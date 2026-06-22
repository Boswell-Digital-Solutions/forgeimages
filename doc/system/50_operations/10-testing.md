# §10 — Testing

## Test Suite Overview

| Layer | Tests | File | Framework |
|-------|-------|------|-----------|
| Rust invariants | 6 | `forgeimages-core/tests/invariants.rs` | cargo test |
| Rust inline | 3 | `forgeimages-core/src/hashing.rs` | cargo test |
| Python boundaries | 20+ | `forgeagents-forgeimages/tests/test_agent_boundary.py` | pytest |

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

## Running Tests

```bash
# Rust tests (all)
cd forgeimages-core && cargo test

# Rust invariant tests only
cd forgeimages-core && cargo test --test invariants

# Python tests
cd forgeagents-forgeimages && pytest tests/ -v

# Python tests with coverage
cd forgeagents-forgeimages && pytest tests/ -v --cov=bridge --cov=skill
```

## Test Philosophy

1. **Invariant tests verify laws, not features.** Each test maps to one of the Six Laws.
2. **Boundary tests verify trust boundaries.** Each test verifies that agents cannot bypass enforcement.
3. **No mocks of the core engine.** Bridge tests may mock the CLI subprocess, but invariant tests use the real pipeline.
4. **Exit code 2 is sacred.** Tests verify that validation failures always produce exit code 2, never exit code 1 or 0.

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
- [x] Boundary tests (20+ Python enforcement tests)
- [ ] Tauri integration for VibeForge
- [ ] MCP tool definitions

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

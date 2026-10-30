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

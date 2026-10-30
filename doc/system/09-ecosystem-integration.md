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

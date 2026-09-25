# §8 — Ecosystem Integration

## Integration Map

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  VibeForge   │     │ ForgeAgents  │     │ AuthorForge  │
│ (consumer)   │     │ (orch.)      │     │ (future)     │
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

## VibeForge Integration (Planned)

VibeForge is the primary consumer of ForgeImages. The planned integration:

- **Prompt-to-image workflows** — VibeForge generates image candidates via AI, ForgeImages validates and compiles them
- **Tauri IPC** — Future Tauri commands will wrap ForgeImages operations for desktop use
- **Template browsing** — VibeForge UI will display available templates and their constraints

**Status:** Not yet implemented. Requires Tauri command integration.

## AuthorForge Integration (Future)

AuthorForge will use ForgeImages for:

- **Book covers** — Cover template with specific aspect ratios and export formats
- **Print PDF** — CMYK color space via PrintAuthority
- **Chapter illustrations** — Banner/icon templates for digital and print
- **Print bleed** — Physical bleed specifications from PrintSpec

**Status:** Not yet implemented. Requires CMYK export pipeline and print templates.

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
| Input | JSON via `--payload` flag |
| Output | JSON on stdout |
| Exit 0 | Success |
| Exit 2 | Validation/compilation failure |
| Exit 1 | System error |
| Timeout | 30 seconds |

# §5 — Configuration & Environment

## Bridge Environment Variables

All bridge configuration uses the `FORGEIMAGES_` prefix via pydantic-settings.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `FORGEIMAGES_CLI_PATH` | Path | `../forgeimages-core/target/release/forgeimages-cli` | Path to compiled Rust CLI binary |
| `FORGEIMAGES_TEMPLATES_DIR` | Path | `../forgeimages-core/templates` | Directory containing template JSON files |
| `FORGEIMAGES_AUDIT_LOG_PATH` | Path | `./audit.jsonl` | Audit log output file |
| `FORGEIMAGES_MAX_REQUEST_SIZE_MB` | int | `10` | Maximum HTTP request body size |
| `FORGEIMAGES_MAX_PAYLOAD_SIZE_KB` | int | `512` | Maximum JSON payload size |
| `FORGEIMAGES_ENGINE_VERSION` | str | `"1.0.0"` | Engine version for audit logging |

## CLI Flags

### Global Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--templates-dir` | `templates` | Directory containing template JSON files |

### Validate Subcommand

| Flag | Required | Description |
|------|----------|-------------|
| `--template` | Yes | Template ID to validate against |
| `--payload` | Yes | JSON string of AssetInput |

### Compile Subcommand

| Flag | Required | Description |
|------|----------|-------------|
| `--template` | Yes | Template ID to compile against |
| `--payload` | Yes | JSON string of CompileRequest |

## Template Configuration (pwa-icon.json)

Templates are JSON files in the templates directory. Each template defines:

```json
{
  "id": "pwa-icon",
  "name": "PWA Icon Pack",
  "templateVersion": "1.0.0",
  "engineMinVersion": "1.0.0",
  "assetClass": "icon",
  "aspectRatio": [1, 1],
  "canonicalSize": [1024, 1024],
  "vectorMaster": true,
  "validation": {
    "required": true,
    "failureMode": "block",
    "rules": {
      "aspectRatio": { "enabled": true, "tolerance": 0.01 },
      "resolution": { "enabled": true, "minWidth": 512, "minHeight": 512 },
      "colorCount": { "enabled": true, "maxColors": 16 }
    }
  },
  "exports": [
    { "id": "master", "size": [1024, 1024], "format": "svg", "required": true },
    { "id": "favicon-16", "size": [16, 16], "format": "png", "required": true },
    { "id": "favicon-32", "size": [32, 32], "format": "png", "required": true },
    { "id": "apple-touch", "size": [180, 180], "format": "png", "required": true },
    { "id": "pwa-192", "size": [192, 192], "format": "png", "required": true },
    { "id": "pwa-512", "size": [512, 512], "format": "png", "required": true }
  ]
}
```

## Rust Constants

| Constant | Value | Location |
|----------|-------|----------|
| `ENGINE_VERSION` | `env!("CARGO_PKG_VERSION")` → `"1.0.0"` | `lib.rs` |
| `MIN_TEMPLATE_VERSION` | `"1.0.0"` | `lib.rs` |

## Default Validation Tolerances

| Rule | Default | Description |
|------|---------|-------------|
| Aspect ratio tolerance | 0.01 (1%) | Quantization bucket for ratio comparison |
| Min resolution | 1024x1024 | Default minimum (overridden by template) |
| Max color count | 16 | Default maximum (overridden by template) |

## Print Defaults

| Setting | Default | Valid Range |
|---------|---------|-------------|
| DPI | 300 | 72-1200 |
| Color space | RGB | RGB, CMYK, Grayscale |
| Bleed | 0.125 inches | 0-1 inch |

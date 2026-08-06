# §6 — API Layer

## Bridge HTTP Endpoints

The bridge service runs on `http://127.0.0.1:8100` (configurable via uvicorn).

### Endpoint Reference

| Method | Endpoint | Purpose | Success | Failure |
|--------|----------|---------|---------|---------|
| GET | `/health` | Health check | 200 | — |
| GET | `/templates` | List all templates | 200 `list[TemplateInfo]` | — |
| GET | `/template/{id}` | Get template details | 200 `dict` | 404 |
| POST | `/validate/{id}` | Validate asset against template | 200 `ValidationResult` | 422 |
| POST | `/compile/{id}` | Compile asset (validates first) | 200 `CompileResponse` | 422 |

### Request/Response Models

**POST /validate/{template_id}**
```json
// Request body (AssetInput)
{
  "width": 512,        // 1-10000
  "height": 512,       // 1-10000
  "color_count": 8,    // optional, 1-256
  "format": "png"      // optional
}

// Success response (ValidationResult)
{
  "valid": true,
  "violations": [],
  "template_id": "pwa-icon",
  "template_version": "1.0.0"
}

// Failure response (HTTP 422)
{
  "valid": false,
  "violations": [
    {
      "rule": "aspect_ratio",
      "severity": "error",
      "message": "Aspect ratio 2.00 exceeds tolerance ...",
      "expected": "1.00",
      "actual": "2.00",
      "remediation": ["Resize to 1:1 aspect ratio"]
    }
  ],
  "template_id": "pwa-icon",
  "template_version": "1.0.0"
}
```

**POST /compile/{template_id}**
```json
// Request body (CompileRequest)
{
  "template_id": "pwa-icon",
  "asset_input": { "width": 512, "height": 512, "color_count": 8 },
  "source_data": "base64...",   // optional
  "seed": 42,                   // optional
  "prompt": "..."               // optional, max 2000 chars
}

// Success response (CompileResponse)
{
  "success": true,
  "asset": {
    "id": "uuid",
    "template_id": "pwa-icon",
    "template_version": "1.0.0",
    "engine_version": "1.0.0",
    "created_at": "2026-01-15T12:00:00Z",
    "manifest_hash": "sha256:...",
    "job_hash": "sha256:...",
    "validation": { "valid": true, "violations": [] },
    "exports": [
      {
        "id": "master",
        "filename": "master.svg",
        "format": "svg",
        "size": [1024, 1024],
        "data_base64": "...",
        "hash": "sha256:..."
      }
    ]
  }
}
```

### `source_data` — supplying a master

`source_data` carries a base64 master asset. It is optional; when present it is
**authoritative**, and the governing rule is:

> A supplied master is never silently ignored. If it cannot be decoded, is not
> admissible for the template, or cannot be converted to a required export, the
> compile **fails**. It never falls back to the placeholder export.

That rule exists because the opposite was previously true: `source_data` was
accepted, transported and canonicalized into `job_hash`, but read by no code — so
a caller who supplied a master received a placeholder asset accompanied by a hash
asserting the master had been compiled.

**Accepted masters** — SVG markup (tolerating a BOM/XML prolog), or a raster
decodable by the enabled `image` features (PNG/JPEG/TIFF). Sniffing alone is not
enough: the raster is fully decoded up front, so a truncated file carrying a
valid magic number is rejected here rather than failing later during encoding.

**Admissibility**, checked before any export is produced:

| Condition | Result |
|---|---|
| Template declares `vectorMaster: true` and the master is raster | Refused — Law 1, *SVG Is Truth* |
| `asset_input` dimensions differ from the master's real dimensions | Refused — validation ran against an asset that is not the one being compiled |

**Conversions implemented** (both deterministic, Law 4):

| Master | Export | Behaviour |
|---|---|---|
| SVG | `svg` | Pass-through |
| Raster | `png` / `jpg`, size matches | Pass-through (no re-encode, so the hash stays stable) |
| Raster | `png` / `jpg`, size differs | Lanczos3 resize + re-encode |
| Raster (opaque grayscale) | `pdf` | **PDF/X-1a:2001** via the deterministic writer (`pdf.rs`): the master is embedded at 300 DPI with `MediaBox`/`TrimBox`/`OutputIntent` and no transparency |

Everything else is **refused explicitly** rather than approximated: an SVG master
to `pdf` (no rasterizer), raster→`ico`, and — the case that matters for covers —
a **non-grayscale** raster to `pdf`. PDF/X-1a is a device grayscale/CMYK print
standard, and turning an RGB diffusion master into CMYK is a color-managed step
ForgeImages will not invent; it refuses with that reason rather than emit a
"print-ready" file built on made-up color. So `book-cover-kdp` (whose PDF/X-1a
export is `required`) now compiles from a supplied **grayscale** cover master and
refuses precisely for an RGB one — the remaining gate is a chosen RGB→CMYK output
intent, not a missing writer. See §7 for the writer's conformance boundary.

**When `source_data` is absent**, behaviour is unchanged: exports are placeholders
(an empty `<svg>`, a 1x1 PNG, or `b"placeholder"`), because export *rendering* is
still unimplemented. That predates this change and is not widened by it — but it
does mean a no-master compile of `book-cover-kdp` still returns a placeholder for
a file described as print-ready.

### Error Semantics

| HTTP Status | Meaning | When |
|-------------|---------|------|
| 200 | Success | Valid asset or successful compilation |
| 404 | Not found | Template ID does not exist |
| 422 | Validation failure | Asset violates template rules (blocking mode) |
| 503 | Service unavailable | Rust CLI binary not found |
| 504 | Timeout | CLI execution exceeded 30 seconds |

### Middleware

- **Request size limiter** — Enforces `max_request_size_mb` (default 10 MB)

### Headers

| Header | Direction | Purpose |
|--------|-----------|---------|
| `X-User-ID` | Request | Optional user identification for audit trail |
| `Content-Type` | Both | `application/json` |

## CLI Subcommands

The Rust CLI is invoked by the bridge as a subprocess. It is also usable directly.

### `templates` — List Templates

```bash
forgeimages-cli templates --templates-dir ./templates
```

Output: JSON array of template summaries.

### `validate` — Validate Asset

```bash
forgeimages-cli validate \
  --template pwa-icon \
  --payload '{"width":512,"height":512,"color_count":8}' \
  --templates-dir ./templates
```

Output: JSON ValidationResult. Exit code 0 = valid, exit code 2 = invalid.

### `compile` — Compile Asset

```bash
forgeimages-cli compile \
  --template pwa-icon \
  --payload '{"template_id":"pwa-icon","asset_input":{"width":512,"height":512,"color_count":8}}' \
  --templates-dir ./templates
```

Output: JSON CompiledAsset. Exit code 0 = success, exit code 2 = validation/compilation failure.

### CLI Exit Code Semantics

| Code | Meaning | Bridge Interpretation |
|------|---------|----------------------|
| 0 | Success | HTTP 200 |
| 1 | System error | HTTP 500 |
| 2 | Validation failure | HTTP 422 |

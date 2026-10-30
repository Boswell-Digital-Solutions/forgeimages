# §14 — Known Gaps & Future-Work Tally

This chapter lists what the code does **not** do yet, or does in a way a reader could mistake for more than it is. Each entry was checked against source on 2026-10-30. Formal defect records live in `docs/KNOWN_ISSUES.md` (`KI-IMG-*`). An entry here is not a KI unless it says so.

## Output Fidelity

| # | Gap | Where | Effect |
| --- | --- | --- | --- |
| G1 | A compile **without** `source_data` returns placeholder exports: an empty `<svg>`, a 1×1 PNG, or the literal bytes `placeholder` for JPG/PDF/ICO | `pipeline.rs` `render_export` | The response reports `success: true` with real hashes. For `book-cover-kdp`, the `required` `cover-pdf` is the bytes `placeholder`. Callers must supply a master to get real files |
| G2 | No SVG rasterizer | `source_master.rs` | An SVG master produces only SVG exports. `pwa-icon` (vector master required, five PNG exports) cannot produce a real icon set. The separate `Forge_Images` repository has a `resvg`-based renderer that has not been ported here |
| G3 | ICO export is refused from every master | `source_master.rs` | No template ships an ICO export today, so nothing breaks yet |
| G4 | PDF/X-1a is admitted only from opaque 8-bit grayscale masters | `source_master.rs` | RGB masters are refused by design (no colour-managed RGB→CMYK). The writer can represent CMYK, but no ingest path accepts a CMYK master yet. A colour book cover cannot compile to print |
| G5 | The PDF output intent is named, not embedded (`kdp_us_swop`) | `pdf.rs` | Structurally PDF/X-1a:2001. Strict vendor preflight may want an embedded ICC profile. Not verified against a real RIP |

## Validation Coverage

| # | Gap | Where | Effect |
| --- | --- | --- | --- |
| G6 | `DimensionMatchRule`, `ColorSpaceRule`, `FileSizeRule`, `CoverTemplateParams`, `ValidationOutcome` and `PrintSpec` are public API that no caller wires in | `rules/`, `cover_params.rs`, `validation_outcome.rs`, `print.rs` | `book-cover-kdp` is validated on aspect ratio and minimum resolution only. Spine width, exact trim size, colour space and file size are not checked on any served path |
| G7 | `FailureMode::Log` behaves exactly like `Warn` | `validation.rs` | The two modes cannot be told apart in output |
| G8 | `TemplateRegistry::load_from_dir` skips unreadable or unparseable files silently | `templates.rs` | A broken template surfaces later as `Template not found`, with no load-time error |
| G9 | The colour-count rule never runs on the Tauri file path | `file_validation.rs` | `color_count` is always `None` there |

## Bridge and Interfaces

| # | Gap | Where | Effect |
| --- | --- | --- | --- |
| G10 | `/compile` returns 422 for every engine error | CLI + bridge | A rule failure, an unknown template and a refused master share one status. Distinguish them by `detail.error` |
| G11 | `FORGEIMAGES_MAX_PAYLOAD_SIZE_KB` is declared and never read | `settings.py` | Only the 10 MB request limit applies |
| G12 | The validate audit `job_hash` uses the bridge's configured `engine_version`, not the CLI's | `forgeimages_bridge.py` | If the two diverge, the audit hash names the wrong engine |
| G13 | Tauri `TemplateInfo.asset_class` uses the `Debug` form (`characterportrait`), and the CLI uses the serde form (`character_portrait`) | `forgeimages-tauri/src/commands.rs` | Multi-word classes do not match across the two paths |
| G14 | Cloud-fulfillment contracts, profiles, validator and manifest are not served | `bridge/cloud_fulfillment_*` | Slice 03 (replacement feedback, initially with stubs and mocks) is the next governed step |
| G15 | `Settings` uses Pydantic's class-based `Config` | `settings.py` | A deprecation warning on every test run; it breaks in Pydantic v3 |

## Verification and Delivery

| # | Gap | Where | Effect |
| --- | --- | --- | --- |
| G16 | CI does not run the Python test suite | `.github/workflows/freeze.yml` | Bridge, skill and cloud-fulfillment regressions are caught only locally |
| G17 | CI is path-filtered to `packaging/`, `bridge/`, `forgeimages-core/` and the Cargo files | `freeze.yml` | A change confined to `forgeimages-tauri/` or `skill/` triggers no CI |
| G18 | `forgeimages-tauri` has no tests | `forgeimages-tauri/` | The empty-registry fallback and lock handling are unexercised |
| G19 | AuthorForge bundles its own copies of the templates | AuthorForge `src-tauri/forgeimages-templates/` | The desktop path and the sidecar path can validate against different contract versions |

## Not Planned Here

- **Image generation.** It belongs to NeuronForge Local and NeuroForge.
- **Colour-managed conversion.** ForgeImages refuses instead of inventing colour. A conversion step would be a deliberate new capability with its own profile authority.
- **VibeForge integration.** Unscheduled. No consumer exists (§9).
- **MCP tool definitions.** Proposed in earlier plans. No work has started.

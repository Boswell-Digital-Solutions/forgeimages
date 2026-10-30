# §4 — Project Structure

## Directory Tree

```
forgeimages/
├── README.md                          # Overview, Documentation Contract, quick start
├── CLAUDE.md                          # Agent contract: Six Laws, verification, non-obvious rules
├── LICENSE                            # Proprietary, Boswell Digital Solutions LLC
├── Cargo.toml / Cargo.lock            # Workspace (core + tauri); lock is tracked
├── .github/workflows/freeze.yml       # Engine tests + frozen-sidecar build and qualification
│
├── doc/
│   ├── system/                        # Canonical source of truth (this document)
│   │   ├── _index.md                  # Header, truth classes, chapter table
│   │   ├── NN-*.md                    # 18 flat numbered chapters
│   │   ├── system_manifest.json       # Machine section map (bds.repo_doc_system_manifest.v1)
│   │   ├── BUILD.sh                   # Fail-closed assembly
│   │   └── validate_snapshots.sh      # Snapshot and manifest/index validation
│   └── imgSYSTEM.md                   # Generated: assembled reference (do not edit)
│
├── docs/
│   ├── KNOWN_ISSUES.md                # KI-IMG-* findings, root causes, scope
│   ├── forgeimages_architecture_spec.md   # Design intent (subordinate to doc/system/)
│   └── forgeimages_extended_roadmap.md    # Roadmap (subordinate to doc/system/)
│
├── reports/forgeimages-verification/  # Dated evidence: cloud-image Slice 01 and 02
├── files/                             # Pre-implementation design specs (historical)
├── scripts/context-bundle.sh          # AI session context generator
│
├── packaging/                         # Frozen forgeimages-bridge sidecar (§12)
│   ├── build.sh                       # One-commit build: CLI (--locked) + bridge + templates
│   ├── forgeimages-bridge.spec        # PyInstaller spec
│   ├── freeze_entry.py                # Sidecar entry point, --runtime-info, env contract
│   ├── freeze_env.sh                  # Shared CPython 3.12 helper (same as forge-neuronforge)
│   ├── qualify_frozen.py              # Runs and checks the frozen binary
│   └── requirements-freeze.{in,txt}   # Hashed universal lock
│
├── forgeimages-core/                  # Rust engine (v1.0.0, edition 2024)
│   ├── src/
│   │   ├── lib.rs                     # Six Laws, public re-exports, ENGINE_VERSION
│   │   ├── templates.rs               # Template contract types, TemplateRegistry
│   │   ├── validation.rs              # ValidationRule trait, 3 default rules, Validator + failure-mode policy
│   │   ├── rules/                     # Rule library: aspect_ratio, resolution, color_count,
│   │   │                              #   dimensions, color_space, file_size (not in the default Validator)
│   │   ├── pipeline.rs                # CompilationPipeline: validate → master → exports → hashes
│   │   ├── source_master.rs           # Decode, identify, admit and convert a caller's master
│   │   ├── pdf.rs                     # Deterministic raster → PDF/X-1a:2001 writer
│   │   ├── hashing.rs                 # Canonical JSON, SHA-256, job/manifest hashes, provenance types
│   │   ├── print.rs                   # PrintAuthority, PrintSpec, ColorSpace
│   │   ├── cover_params.rs            # Book-cover spine/bleed dimension resolver
│   │   ├── validation_outcome.rs      # ScreenOnly / PrintReady / PrintAdvisory / Draft / Rejected
│   │   ├── file_validation.rs         # Read real dimensions/format from a file (Tauri path)
│   │   └── bin/forgeimages_cli.rs     # CLI: templates, validate, compile; --payload - reads stdin
│   ├── templates/                     # 5 template contracts (§8)
│   └── tests/
│       ├── invariants.rs              # 6 contract invariants
│       ├── source_master.rs           # 19 master ingestion / conversion tests
│       └── cli_payload.rs             # 3 stdin payload tests
│
├── forgeimages-tauri/                 # Tauri 2 IPC commands for AuthorForge (§7)
│   └── src/{lib.rs, commands.rs}
│
└── forgeagents-forgeimages/           # Python package (v1.0.0, Python >=3.10, hatchling)
    ├── bridge/                        # FastAPI bridge + audit + cloud-fulfillment contracts
    ├── skill/                         # ForgeImagesSkill async httpx client
    └── tests/                         # Boundary, CLI payload, cloud-fulfillment tests
```

## Key Module Responsibilities

> Line counts are snapshot facts, counted 2026-10-30.

### Rust Modules (`forgeimages-core/src/`)

| Module | Lines | Responsibility |
|--------|-------|----------------|
| `lib.rs` | 37 | Six Laws docstring, public API re-exports, `ENGINE_VERSION`, `MIN_TEMPLATE_VERSION` |
| `templates.rs` | 196 | `Template`, `AssetClass`, `ValidationConfig`, `FailureMode`, `ExportSpec`, `ExportFormat`, `TemplateRegistry` |
| `validation.rs` | 244 | `ValidationRule` trait, `AspectRatioRule`, `ResolutionRule`, `ColorCountRule`, `Validator` (policy) |
| `rules/` | 407 | Per-rule modules, including `DimensionMatchRule`, `ColorSpaceRule`, `FileSizeRule` for Cover Forge |
| `pipeline.rs` | 317 | `CompilationPipeline`, `CompileRequest`, `CompiledAsset`, `ExportedFile`, `PipelineError` |
| `source_master.rs` | 402 | `decode`, `check_admissible`, `render_export`, `SourceMasterError` |
| `pdf.rs` | 770 | `write_pdf_x1a`, `DeviceColor`, `OutputIntent`, `IccProfile`, `PrintGeometry` |
| `hashing.rs` | 165 | `canonical_json`, `sha256_hex`, `compute_job_hash`, `compute_manifest_hash`, `SourceType`, `AssetManifest` |
| `print.rs` | 80 | `PrintAuthority`, `PrintSpec`, `ColorSpace` |
| `cover_params.rs` | 162 | `CoverTemplateParams`, `PaperStock`, `ResolvedCoverDimensions` |
| `validation_outcome.rs` | 62 | `ValidationOutcome` clearance levels |
| `file_validation.rs` | 54 | `validate_from_file` |
| `bin/forgeimages_cli.rs` | 181 | Clap CLI, exit-code contract |
| `forgeimages-tauri/src/commands.rs` | 96 | 3 Tauri commands, `ForgeImagesState`, `init_state` |

### Python Modules (`forgeagents-forgeimages/`)

| Module | Lines | Responsibility |
|--------|-------|----------------|
| `bridge/forgeimages_bridge.py` | 275 | FastAPI app, 5 endpoints, `call_cli` (payload on stdin), size-limit middleware |
| `bridge/models.py` | 110 | Pydantic v2 models mirroring the Rust types |
| `bridge/audit.py` | 104 | Append-only JSONL audit log with job hash |
| `bridge/settings.py` | 32 | `FORGEIMAGES_*` configuration |
| `bridge/cloud_fulfillment_contracts.py` | 168 | Strict v1 request/result/rejection/compiled-asset records |
| `bridge/cloud_fulfillment_profiles.py` | 118 | Immutable validation profile registry |
| `bridge/cloud_fulfillment_validation.py` | 296 | `DeterministicCloudAssetValidator` |
| `bridge/cloud_fulfillment_manifest.py` | 76 | Self-verifying `ForgeImagesAssetManifestV1` |
| `skill/forgeimages_skill.py` | 377 | `ForgeImagesSkill`, `ForgeImagesError`, result wrappers |

# §4 — Project Structure

## Directory Tree

```
ForgeImages/
├── README.md                          # Project overview and quick start
├── CLAUDE.md                          # AI assistant coding standards
├── .gitignore                         # Build artifacts, venvs, audit logs
│
├── doc/                               # Forge Documentation Protocol docs
│   ├── system/                        # Modular system documentation parts
│   │   ├── _index.md                  # Master table of contents
│   │   ├── 01-overview-philosophy.md  # §1: Six Laws, ecosystem role
│   │   ├── 02-architecture.md         # §2: Trust boundary, data flow
│   │   ├── 03-tech-stack.md           # §3: Dependencies and versions
│   │   ├── 04-project-structure.md    # §4: This file
│   │   ├── 05-config-env.md           # §5: Environment and CLI flags
│   │   ├── 06-api-layer.md            # §6: Bridge endpoints, CLI commands
│   │   ├── 07-backend-internals.md    # §7: Template, validation, hashing, pipeline
│   │   ├── 08-ecosystem-integration.md # §8: ForgeAgents, VibeForge, AuthorForge
│   │   ├── 09-error-handling.md       # §9: 422 contract, exit codes, violations
│   │   ├── 10-testing.md             # §10: Invariant + boundary tests
│   │   ├── 11-handover.md            # §11: Constraints, deployment, future
│   │   └── BUILD.sh                   # Assembles parts into context-bundle.md
│   └── SYSTEM.md                      # Generated: full assembled reference
│
├── scripts/
│   └── context-bundle.sh             # AI session context generator (presets)
│
├── files/                             # Design documentation (pre-implementation)
│   ├── README.md                      # ForgeAgents integration guide
│   ├── CONTEXT.md                     # Trust boundary architecture
│   ├── step1-rust-core.md             # Rust core design spec
│   ├── step2-rust-cli.md              # CLI design spec
│   ├── step3-python-bridge.md         # Bridge service design spec
│   ├── step4-python-skill.md          # Skill wrapper design spec
│   ├── step5-tests.md                 # Test strategy spec
│   └── VSCODE_CLAUDE_PROMPT.md        # Implementation prompt
│
├── forgeimages-core/                  # Rust core engine
│   ├── Cargo.toml                     # Package: forgeimages-core v1.0.0, edition 2024
│   ├── src/
│   │   ├── lib.rs                     # Library root — Six Laws, public API exports
│   │   ├── templates.rs               # Template contracts (TemplateRegistry, AssetClass, ExportSpec)
│   │   ├── validation.rs              # Rule/policy separation (3 rules, Validator, FailureMode)
│   │   ├── hashing.rs                 # SHA-256 manifests (canonical JSON, job_hash, manifest_hash)
│   │   ├── print.rs                   # PrintAuthority enum (System/Template/User, DPI/CMYK)
│   │   ├── pipeline.rs               # CompilationPipeline (compile ALWAYS validates, exports)
│   │   └── bin/
│   │       └── forgeimages_cli.rs     # CLI binary (templates, validate, compile subcommands)
│   ├── templates/
│   │   └── pwa-icon.json              # PWA icon template (1:1, 512px min, 6 PNG + 1 SVG)
│   └── tests/
│       └── invariants.rs              # Contract invariant tests (6 tests)
│
└── forgeagents-forgeimages/           # Python agent integration
    ├── pyproject.toml                 # Package: forgeagents-forgeimages v1.0.0, Python >=3.10
    ├── bridge/                        # FastAPI bridge service
    │   ├── __init__.py                # Package init
    │   ├── forgeimages_bridge.py      # HTTP endpoints (health, templates, validate, compile)
    │   ├── models.py                  # Pydantic v2 models (AssetInput, CompileRequest, etc.)
    │   ├── settings.py                # Configuration (FORGEIMAGES_ env prefix)
    │   └── audit.py                   # Append-only JSONL audit logging
    ├── skill/                         # ForgeAgents skill wrapper
    │   ├── __init__.py                # Package init
    │   └── forgeimages_skill.py       # ForgeImagesSkill class (async httpx client)
    └── tests/
        └── test_agent_boundary.py     # Agent boundary enforcement tests (20+ tests)
```

## Key Module Responsibilities

### Rust Modules

| Module | LOC | Responsibility |
|--------|-----|----------------|
| `lib.rs` | 25 | Six Laws docstring, public API re-exports, version constants |
| `templates.rs` | 176 | Template, AssetClass, ValidationConfig, ExportSpec, TemplateRegistry |
| `validation.rs` | 224 | 3 rules (AspectRatio, Resolution, ColorCount), Validator, FailureMode |
| `hashing.rs` | 102 | SHA-256, canonical JSON (sorted keys), job_hash, manifest_hash |
| `print.rs` | 81 | PrintAuthority enum, PrintSpec, ColorSpace, DPI/bleed validation |
| `pipeline.rs` | 272 | CompilationPipeline, CompileRequest, CompiledAsset, ExportedFile |
| `forgeimages_cli.rs` | 149 | Clap CLI: templates, validate (exit 2), compile (exit 2) |

### Python Modules

| Module | LOC | Responsibility |
|--------|-----|----------------|
| `models.py` | 93 | Pydantic v2 models mirroring Rust types |
| `settings.py` | 33 | Environment-based config (FORGEIMAGES_ prefix) |
| `audit.py` | 105 | Append-only JSONL audit log with job hash linkage |
| `forgeimages_bridge.py` | 272 | FastAPI app with 5 endpoints, CLI subprocess calls |
| `forgeimages_skill.py` | 378 | ForgeImagesSkill class, async httpx, error handling |

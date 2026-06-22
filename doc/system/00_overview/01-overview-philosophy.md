# §1 — Overview & Philosophy

## Service Identity

**ForgeImages** is the template-driven image asset pipeline for the Forge Ecosystem. It provides deterministic, auditable image asset generation with strict validation enforcement and a clear separation between agent suggestions and system enforcement.

- **Version:** v1.0.0
- **Status:** Implemented (core engine + bridge + skill)
- **Languages:** Rust 2024 (core engine + CLI), Python 3.10+ (agent bridge + skill)
- **LOC:** ~2,400 (Rust ~1,100, Python ~800, Tests ~500)

## The Six Laws (Non-Negotiable)

These are the canonical invariants. Every code path, every test, every design decision traces back to one of these laws.

1. **SVG Is Truth** — Vector masters are the canonical source; all raster exports derive from them.
2. **Templates Are Contracts** — Old templates work forever. New engines never silently change behavior. Version mismatch = clear error.
3. **Validation Is Protective** — Validation exists to catch errors before they propagate, not to punish users.
4. **Deterministic Output** — Same inputs always produce the same outputs. Manifest hashes are stable and reproducible.
5. **Manifests Enable Reproduction** — SHA-256 hashes link inputs to outputs for legal defensibility and auditability.
6. **Agents Suggest, Engine Enforces** — AI agents can generate and select candidates, but all validation and compilation must pass through ForgeImages' template-defined rules. No bypasses allowed.

## Core Principle

> **Agents suggest, ForgeImages enforces.**

This is not a guideline. It is an architectural invariant enforced at three levels:

1. **Rust type system** — `compile_asset()` always calls `validate_asset()` internally
2. **HTTP status codes** — Bridge returns 422 on validation failure; agents cannot proceed
3. **CLI exit codes** — Exit code 2 = validation failure; bridge interprets this as 422

## Ecosystem Role

```
┌──────────────────────────────────────────────────────────────┐
│                      Forge Ecosystem                          │
│                                                              │
│   VibeForge     ForgeAgents     AuthorForge                 │
│   (consumer)    (orchestration)  (future)                    │
│       │              │              │                        │
│       └──────────────┴──────────────┘                        │
│                      │                                       │
│          ┌───────────▼────────────┐                          │
│          │   ForgeImages Bridge   │  ← HTTP gateway          │
│          │   (Python / FastAPI)   │                          │
│          └───────────┬────────────┘                          │
│                      │ subprocess                            │
│          ┌───────────▼────────────┐                          │
│          │   ForgeImages Core     │  ← Validation + compile  │
│          │   (Rust 2024)          │                          │
│          └────────────────────────┘                          │
└──────────────────────────────────────────────────────────────┘
```

## What ForgeImages Is

- **A validation engine** — Enforces template-defined rules on image assets
- **A compilation pipeline** — Produces deterministic, hashed export bundles
- **An audit trail** — Every request is logged with job hashes linking inputs to outputs
- **A trust boundary** — Agents interact through the skill/bridge layer; they never touch the engine directly

## What ForgeImages Is Not

- **Not an image editor.** It does not provide editing tools; it validates and compiles assets.
- **Not a storage service.** Compiled assets are returned as base64; persistence is the caller's responsibility.
- **Not an AI model.** It does not generate images; agents upstream (VibeForge) handle generation.
- **Not a CDN.** It produces export bundles; distribution is handled elsewhere.

## Codebase Metrics

| Metric | Count |
|--------|-------|
| Rust source files | 7 (lib + 5 modules + CLI) |
| Python source files | 6 (bridge: 4, skill: 1, init: 1) |
| Test files | 2 (Rust invariants + Python boundaries) |
| Template files | 1 (pwa-icon.json) |
| Validation rules | 3 (AspectRatio, Resolution, ColorCount) |
| CLI subcommands | 3 (templates, validate, compile) |
| Bridge endpoints | 5 (health, templates, template/:id, validate/:id, compile/:id) |
| Test methods | 26+ (Rust: 6 invariant, Python: 20+ boundary) |

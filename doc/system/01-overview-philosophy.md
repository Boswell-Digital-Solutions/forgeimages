# §1 — Overview & Philosophy

> **System identity — bds family (Boswell Digital Solutions business system, local-systems tier).** ForgeImages is the template-driven image asset pipeline for the Forge ecosystem, implemented as a Rust engine with a Python bridge in `ecosystem/local-systems`.

## Service Identity

**ForgeImages** validates and compiles image assets against versioned template contracts. Every compile produces hashed exports and a manifest that ties the output to its inputs. AI systems may generate and select candidates. ForgeImages decides whether a candidate is admissible and produces the deliverable files.

| Property | Value |
| --- | --- |
| Designation | `img` (registered in the forge meta-repo `doc/PREFIX_REGISTRY.md`) |
| Engine version | `1.0.0` (`forgeimages-core`, `ENGINE_VERSION`) |
| Languages | Rust 2024 (engine, CLI, Tauri commands); Python 3.10+ (bridge, skill, cloud-fulfillment contracts) |
| Deployment | Library inside the AuthorForge desktop app, plus a frozen HTTP sidecar (`forgeimages-bridge`) in AuthorForge release bundles |
| Network posture | Bridge binds loopback only (`127.0.0.1:8100`) and has no authentication |
| State | Stateless, apart from the append-only audit log the bridge writes |

Not to be confused with `Forge_Images` (underscore, designation `ima`), a separate repository with a different git remote whose code has forked from this one. AuthorForge vendors **this** repository as the `third_party/forgeimages` submodule.

## The Six Laws (Non-Negotiable)

These are the canonical invariants. Every code path, test and design decision traces back to one of them.

1. **SVG Is Truth.** Vector masters are the canonical source. Raster exports derive from them.
2. **Templates Are Contracts.** Old templates keep working. A new engine never silently changes behavior. A version mismatch is a clear error.
3. **Validation Is Protective.** Validation catches errors before they spread. It is not there to punish users.
4. **Deterministic Output.** The same inputs always produce the same output bytes and the same hashes.
5. **Manifests Enable Reproduction.** SHA-256 hashes link inputs to outputs, for audit and legal defensibility.
6. **Agents Suggest, Engine Enforces.** Agents can generate and select candidates. Every validation and compilation goes through the template-defined rules. Nothing bypasses them.

Two working rules follow from the laws and appear throughout the code:

- **A supplied master is never silently ignored.** If a caller's master cannot be decoded, is not admissible, or cannot produce a required export, the compile fails. It does not fall back to a placeholder (§8, `source_master.rs`).
- **ForgeImages does not invent.** It does not generate imagery, and it does not perform colour-managed RGB→CMYK conversion. A conversion it cannot do honestly is refused by name (§8, `pdf.rs`).

## Core Principle

> **Agents suggest, ForgeImages enforces.**

The principle is enforced in three places:

1. **The engine.** `compile_asset()` always calls `validate_asset()` first. No code path skips it.
2. **The CLI.** Exit code `2` means a validation or compilation failure.
3. **The bridge.** Exit code `2` becomes HTTP `422`. An agent cannot proceed past a 422.

## Ecosystem Role

```
 NeuronForge Local image lane      AuthorForge desktop (Tauri)
 (diffusion masters)               (cover / asset validation UI)
          │ HTTP                              │ in-process Rust calls
          ▼                                   ▼
 ┌────────────────────────┐        ┌──────────────────────────┐
 │ forgeimages-bridge     │        │ forgeimages-tauri        │
 │ FastAPI, port 8100     │        │ 3 IPC commands           │
 │ frozen sidecar         │        └────────────┬─────────────┘
 └───────────┬────────────┘                     │
             │ subprocess, payload on stdin      │
             ▼                                   ▼
 ┌──────────────────────────────────────────────────────────┐
 │ forgeimages-core (Rust): templates, validation, source    │
 │ masters, PDF/X-1a writer, hashing, compilation pipeline   │
 └──────────────────────────────────────────────────────────┘
```

ForgeAgents reaches the bridge through the `ForgeImagesSkill` client. NeuroForge cloud fulfillment has versioned contracts and an offline validator in the bridge package. No HTTP route serves them yet (§9).

## What ForgeImages Is

- **A validation engine.** It enforces template-defined rules on image assets.
- **A compilation pipeline.** It produces deterministic, hashed export bundles from a caller's master.
- **A print writer.** It writes structurally conformant PDF/X-1a:2001 files. Today the compile path admits only opaque 8-bit grayscale raster masters. The writer can represent CMYK, but no ingest path produces it yet.
- **An audit trail.** The bridge logs every validate and compile request with a job hash.
- **A trust boundary.** Agents reach the engine only through the skill and the bridge. No file paths cross that boundary.

## What ForgeImages Is Not

- **Not an image generator.** Diffusion and other generative work happen upstream, in NeuronForge Local or NeuroForge.
- **Not an image editor.** It validates, converts and packages. It does not retouch.
- **Not a colour-management system.** It refuses RGB masters for PDF/X-1a instead of converting them.
- **Not a storage service.** Exports are returned as base64. The caller persists them.
- **Not an SVG rasterizer.** This repository has no SVG→raster renderer. An SVG master can only produce SVG exports (§14).

## Codebase Metrics

> Snapshot fact, counted 2026-10-30 at the commit this chapter was written against. Recount before you rely on it.

| Metric | Count |
| --- | --- |
| Rust source files (`forgeimages-core/src`, `forgeimages-tauri/src`) | 21 files, 3,179 lines |
| Python source files (`bridge/`, `skill/`) | 11 files, 1,656 lines |
| Template contracts (`forgeimages-core/templates/`) | 5 |
| Rules wired into the default `Validator` | 3 (aspect ratio, resolution, colour count) |
| CLI subcommands | 3 (`templates`, `validate`, `compile`) |
| Bridge HTTP endpoints | 5 |
| Tauri IPC commands | 3 |
| Rust tests (`cargo test --workspace --features forgeimages-core/test-hooks`) | 51, all passing (§11) |
| Python tests (`pytest tests/`) | 52, all passing (§11) |

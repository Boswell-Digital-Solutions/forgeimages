# ForgeImages — Compiled System Reference

**Designation:** img
**Document role:** Canonical compiled technical reference for the ForgeImages asset validation and compilation pipeline
**Source:** `doc/system/`
**Build command:** `bash doc/system/BUILD.sh`
**Document version:** 3.0 (2026-10-30) — canonicalized to the Forge_Command doc-system shape
**Protocol:** BDS Documentation Protocol v2.0; BDS Repo Documentation System Canonical Compliance Standard

> **Generated artifact warning:** `doc/imgSYSTEM.md` is assembled output. Edit
> the source modules under `doc/system/` and rebuild. Hand edits to the
> compiled artifact are overwritten by the next build.

Assembly contract:

- Command: `bash doc/system/BUILD.sh`
- Validation: `bash doc/system/validate_snapshots.sh` runs during assembly
- Machine source map: `doc/system/system_manifest.json`
- Primary output: `doc/imgSYSTEM.md`

This `doc/system/` tree is the canonical source of truth for ForgeImages
(`Boswell-Digital-Solutions/forgeimages`, the repository AuthorForge vendors as
`third_party/forgeimages`). It is not the documentation for the separate
`Forge_Images` repository (designation `ima`). It uses explicit **truth
classes**: *canonical facts* define role, the Six Laws, authority boundaries,
contracts and invariants; *snapshot facts* are dated, audit-derived counts and
inventories (files, lines, tests, templates, gaps) that drift between audits.
See §15 for the scope and authority order.

`system_manifest.json` is the fail-closed, machine-readable map from owned
repository surfaces to chapters, agent profiles, truth classes and maintenance
triggers. `_index.md` remains the human navigation authority. The build fails if
the two disagree.

| Part | File | Contents |
| --- | --- | --- |
| §1 | `01-overview-philosophy.md` | Service identity, Six Laws, ecosystem role, metrics |
| §2 | `02-architecture.md` | Trust boundary, entry paths, data flow, key decisions |
| §3 | `03-tech-stack.md` | Rust, Tauri, Python and freeze dependencies |
| §4 | `04-project-structure.md` | Directory tree, module responsibilities |
| §5 | `05-config-env.md` | Environment variables, CLI flags, defaults |
| §6 | `06-api-layer.md` | Bridge HTTP endpoints, models, cloud-fulfillment contracts, CLI |
| §7 | `07-tauri-command-interface.md` | Tauri IPC commands consumed by AuthorForge |
| §8 | `08-backend-internals.md` | Templates, validation, source masters, PDF writer, pipeline, hashing, audit |
| §9 | `09-ecosystem-integration.md` | AuthorForge, ForgeAgents, NeuroForge, DataForge contracts |
| §10 | `10-error-handling.md` | 422 contract, error types, exit codes, bridge responses |
| §11 | `11-testing.md` | Test inventory, invariants, running tests |
| §12 | `12-frozen-sidecar.md` | Frozen `forgeimages-bridge` sidecar build and runtime contract |
| §13 | `13-handover.md` | Critical constraints, deployment, status, extension procedures |
| §14 | `14-future-work-tally.md` | Known gaps and deferred work |
| §15 | `15-scope.md` | Scope, truth classes, authority order |
| §16 | `16-governance.md` | Ownership, designation, authority boundaries |
| §17 | `17-change-control.md` | Change workflow, maintenance triggers, defect records |
| §18 | `18-appendices.md` | Glossary, cross-references, revision history |

## Quick Assembly

```bash
bash doc/system/BUILD.sh
```

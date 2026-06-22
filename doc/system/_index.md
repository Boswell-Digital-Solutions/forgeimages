# ForgeImages - Compiled System Reference

**Designation:** IMA
**Document role:** Canonical compiled technical reference for the ForgeImages asset pipeline
**Source:** `doc/system/`
**Build command:** `bash doc/system/BUILD.sh`
**Document version:** 2.0 (2026-06-22) - canonical compliance migration
**Protocol:** BDS Documentation Protocol v2.0; BDS Repo Documentation System Canonical Compliance Standard

> **Generated artifact warning:** `doc/IMASYSTEM.md` is assembled output. Edit
> the source modules under `doc/system/` and rebuild. Hand edits to the
> compiled artifact are overwritten by the next build.

Assembly contract:

- Command: `bash doc/system/BUILD.sh`
- Validation: `bash doc/system/validate_snapshots.sh` runs during assembly
- Primary output: `doc/IMASYSTEM.md`

This `doc/system/` tree is the canonical source of truth for ForgeImages. It
uses explicit **truth classes**: canonical facts define the repo role, authority
boundaries, runtime behavior, service contracts, and verification doctrine;
snapshot facts are dated, audit-derived counts and current implementation
inventory that may drift between audits.

| Part | File | Contents |
| --- | --- | --- |
| §1 | `00_overview/01-overview-philosophy.md` | §1 — Overview & Philosophy |
| §2 | `00_overview/02-architecture.md` | §2 — Architecture |
| §3 | `00_overview/04-project-structure.md` | §4 — Project Structure |
| §4 | `10_service-contract/06-api-layer.md` | §6 — API Layer |
| §5 | `20_runtime/07-backend-internals.md` | §7 — Backend Internals |
| §6 | `20_runtime/09-error-handling.md` | §9 — Error Handling |
| §7 | `30_dependencies/03-tech-stack.md` | §3 — Tech Stack |
| §8 | `30_dependencies/08-ecosystem-integration.md` | §8 — Ecosystem Integration |
| §9 | `40_governance/10-scope.md` | Scope |
| §10 | `40_governance/30-governance.md` | Governance |
| §11 | `40_governance/40-change-control.md` | Change Control |
| §12 | `50_operations/05-config-env.md` | §5 — Configuration & Environment |
| §13 | `50_operations/10-testing.md` | §10 — Testing |
| §14 | `50_operations/11-handover.md` | §11 — Handover |
| §15 | `99_appendices/20-structure.md` | §4 — Project Structure |
| §16 | `99_appendices/90-appendices.md` | Appendices |
| §17 | `99_appendices/91-bootstrap-overview.md` | §1 — Overview & Philosophy |
| §18 | `99_appendices/92-bootstrap-architecture.md` | §2 — Architecture |

## Quick Assembly

```bash
bash doc/system/BUILD.sh
```

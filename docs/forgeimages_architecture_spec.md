# ForgeImages Architecture Spec

**Document version:** 1.0 (2026-04-03) — Baseline protocol adoption

## 1. Purpose

This baseline architecture spec establishes a protocol-compliant design reference for ForgeImages.
It records only repository surfaces directly observable from the current working tree.

## 2. Current Implementation State

| Surface | Current truth |
| --- | --- |
| Canonical technical reference | `doc/system/` plus the generated `doc/imgSYSTEM.md` |
| Repo-local instructions | `CLAUDE.md` |
| Current maturity | Baseline documentation protocol alignment |

## 3. Module Map

| Module | Surface | Current role |
| --- | --- | --- |
| Documentation Stack | `doc/system/`, `doc/imgSYSTEM.md`, `scripts/context-bundle.sh` | Canonical repo context and build surfaces |
| Governance and Specs | `docs/`, `governance/`, `DECISIONS/`, `prompts/`, `evals/`, `analytics/`, or `registry/` | Repo doctrine, experiments, and supporting design material |

## 4. Architectural Boundary

- this document is a baseline and must be expanded as concrete modules, routes, schemas, and integrations are cataloged
- when this spec and `doc/system/` diverge, `doc/system/` wins as the implemented reality reference (see its §15 authority order)

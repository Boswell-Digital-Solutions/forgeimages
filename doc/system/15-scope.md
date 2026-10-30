# §15 — Scope

## What This Document Covers

This `doc/system/` tree is the canonical technical reference for the `forgeimages` repository (designation `img`, git remote `Boswell-Digital-Solutions/forgeimages`). It covers:

- the Rust engine `forgeimages-core`, its CLI, and its template contracts
- the Tauri command crate `forgeimages-tauri`
- the Python package `forgeagents-forgeimages`: bridge, skill and cloud-fulfillment contracts
- the frozen `forgeimages-bridge` sidecar build under `packaging/`, and its CI qualification

## What It Does Not Cover

| Out of scope | Owner |
| --- | --- |
| The separate `Forge_Images` repository (underscore, designation `ima`) | That repository's own `doc/system/` |
| How AuthorForge registers, bundles and launches ForgeImages | AuthorForge `doc/system/` |
| Image generation and the cloud fulfillment saga | NeuronForge Local, NeuroForge |
| Persistence of compiled assets and their metadata | The calling system (DataForge is the ecosystem record store) |
| Fleet documentation protocol, designation registry, doc audits | The forge meta-repo (`doc/BDS_DOCUMENTATION_PROTOCOL_v2.md`, `doc/PREFIX_REGISTRY.md`) |

## Truth Classes

Every statement in this document is one of two classes. `_index.md` declares them.

- **Canonical facts** define role, the Six Laws, authority boundaries, contracts (exit codes, HTTP status mapping, the template schema, the payload-on-stdin rule) and invariants. They change only through §17 and are expected to stay true between audits.
- **Snapshot facts** are dated counts and inventories: file and line counts, test counts and results, the shipped-template table, the gap tally. Each is marked with the date it was taken. They drift as code lands. Recount before relying on one.

## Authority Order

When sources disagree, resolve in this order:

1. **Code and tests** in this repository at the commit in question.
2. **This `doc/system/` tree** and its compiled `doc/imgSYSTEM.md`.
3. `CLAUDE.md` (agent contract) and `README.md` (overview).
4. `docs/forgeimages_architecture_spec.md`, `docs/forgeimages_extended_roadmap.md`, and the historical specs under `files/`. These record intent. They do not override implemented reality.

A disagreement between (1) and (2) is a documentation defect. Fix the chapter (§17). Do not cite the chapter against the code.

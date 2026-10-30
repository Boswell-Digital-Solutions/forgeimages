# §16 — Governance

## Ownership

ForgeImages is owned and operated by Boswell Digital Solutions LLC (proprietary licence, see `LICENSE`). There is a single owner and operator. Every change merges through a pull request to `master` on `Boswell-Digital-Solutions/forgeimages`.

## Designation

| Item | Value |
| --- | --- |
| Designation | `img` |
| Compiled artifact | `doc/imgSYSTEM.md` |
| Registry | forge meta-repo `doc/PREFIX_REGISTRY.md` |
| History | `ima` until 2026-09-24, when the operator resolved a collision with `Forge_Images` (which kept `ima`). The repo emitted the uppercase `IMGSYSTEM.md` until this canonicalization moved it to the lowercase standard the registry records |

The designation appears in exactly four places: `_index.md`, `BUILD.sh` (`DESIGNATION="img"`), `validate_snapshots.sh`, and `system_manifest.json`. A change to it is a registry change first. Update `PREFIX_REGISTRY.md` in the forge meta-repo, then all four files here in one commit.

## Authority Boundaries

| ForgeImages decides | ForgeImages does not decide |
| --- | --- |
| Whether an asset satisfies a template | What image to generate, or which provider generates it |
| Which conversions it will perform, and refusing the rest | Colour management (RGB→CMYK) |
| The template contract schema and the shipped templates | Which ForgeImages commit AuthorForge ships (AuthorForge's submodule pin) |
| The CLI exit-code and bridge HTTP-status contracts | Where compiled assets are stored |

## Change Authority by Surface

| Surface | Rule |
| --- | --- |
| The Six Laws, `compile_asset` → `validate_asset`, CLI exit code `2`, HTTP 422 on exit 2, the append-only audit log | Invariants. A change needs an explicit operator decision recorded in the PR, plus the matching invariant or boundary test change |
| A published template (`id` + `templateVersion`) | Immutable. Ship a new version instead (Law 2) |
| Cloud-fulfillment `*.v1` schemas and rejection codes | Versioned contracts mirrored by NeuroForge. Additive changes need a new schema version, coordinated with NeuroForge |
| Sidecar runtime contract (env vars, port 8100, `--runtime-info`) | Consumed by AuthorForge and NeuronForge Local. Coordinate before changing |
| `Cargo.lock`, `packaging/requirements-freeze.txt` | Regenerate only with the documented commands. Never hand-edit |

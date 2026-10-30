# §17 — Change Control

## Workflow

1. Branch from current `origin/master`.
2. Make the change. Edit chapters under `doc/system/` in the same PR when the change touches anything a chapter describes (see the triggers below).
3. Run the verification set:

   ```bash
   cargo test --workspace --features forgeimages-core/test-hooks
   cd forgeagents-forgeimages && pytest tests/ -q
   bash doc/system/BUILD.sh        # must print BUILD_OK
   ```

4. Commit `doc/imgSYSTEM.md` together with its sources. The compiled file is tracked so that a PR diff shows the documentation change.
5. Open the PR. `freeze.yml` runs on changes to packaging, the bridge, the engine and the Cargo files. It does not run the Python tests (§14 G16), so step 3 is the only Python gate.

## Documentation Maintenance Triggers

`system_manifest.json` maps each chapter to the surfaces it owns and the events that make it stale. The common ones:

| When you change… | Update |
| --- | --- |
| A bridge endpoint, a status mapping, a model field | §6, §10 |
| A Tauri command or `init_state` | §7 |
| Engine modules, conversion rules, the PDF writer | §8, §14 |
| A template file | §8 (shipped-template table), and tell AuthorForge to sync its copy |
| CLI flags or exit codes | §5, §6, §10 |
| A dependency, the Rust edition, the Python floor, the freeze lock | §3 |
| A test file, or test counts | §11 |
| `packaging/` or `freeze.yml` | §12, §3 |
| A gap closed or found | §14, and `docs/KNOWN_ISSUES.md` when it is a defect |

## Defect Records

A defect found in this repository is recorded in `docs/KNOWN_ISSUES.md` as `KI-IMG-YYYYMMDD-NNN`, with date, what is wrong, root cause, fix and scope (open or closed). A defect is closed by the PR that fixes it, and the entry names that change.

## Reaching Consumers

AuthorForge pins this repository as a submodule. A merge here changes nothing in AuthorForge until AuthorForge bumps `third_party/forgeimages` in its own PR. That PR is where a change to the Tauri commands, the sidecar contract or a template reaches users. For templates, AuthorForge also has to copy the file into `src-tauri/forgeimages-templates/`.

## Doc-System Rules

- Chapters are flat `NN-kebab-case.md` files directly under `doc/system/`. `BUILD.sh` fails on any subdirectory or symlink.
- Every chapter appears once in the `_index.md` table and once in `system_manifest.json`. `validate_snapshots.sh` fails the build if the three sets disagree.
- Never hand-edit `doc/imgSYSTEM.md`. Rebuild it.
- Number `00` is reserved. Leave gaps rather than renumbering published chapters without a reason.

# ForgeImages — Known Issues

Findings for this repository: bugs, root causes, gaps, and open tracking state.
Each entry has a date, what is wrong, the root cause, the fix, and an open or closed scope.

## KI-IMG-20261030-001 — the bridge accepts a call from any local caller, a web page included

- Date: 2026-10-30. Found by a static read, recorded in AuthorForge `docs/reports/2026-10-30-support-repo-check.md` as S-2. Not reproduced against a running bridge. Priority: medium (operator ruling, 2026-10-30).
- What is wrong (as found at `56f3ed1`, before `f308cdd`; see the 2026-10-30 update below): `forgeagents-forgeimages/bridge/forgeimages_bridge.py` checks no `Host` header, no `Origin`, and no capability on any route. The only middleware limits the body size (`:77`). `POST /validate/{template_id}` and `POST /compile/{template_id}` run `forgeimages-cli` as a subprocess. The frozen bridge binds `127.0.0.1` (`packaging/freeze_entry.py:111`), which stops other hosts but not a page in the user's browser. A DNS-rebinding page is same-origin and can call both routes. The impact is CPU use and audit-log rows. The caller cannot name a file path, because the Six Laws keep paths off the boundary.
- Root cause: the bridge was written for agents on a trusted host, before it shipped inside AuthorForge. The AuthorForge shell passes it no capability (AuthorForge `src-tauri/src/infrastructure/service_manager.rs:1123`).
- Fix, not done: put a caller boundary in front of the app. The reference contract is forge-neuronforge `service/local_caller_boundary.py` (`LocalCallerBoundary`): one loopback `Host` with the bound port, any `Origin` refused, a per-launch capability compared in constant time. Use a governed shared implementation or an independently verified equivalent. The AuthorForge shell must mint the capability, and AuthorForge callers must send it. Required proof: negative tests, positive tests for the authorized caller, a check against the real AuthorForge caller, and an independent review.
- Fix, in progress (2026-10-30): `bridge/local_caller_boundary.py` ports the reviewed forge-cortex boundary (#27, #28, #30): loopback peer and `Host`, no `Origin`, the per-launch `X-AuthorForge-ForgeImages-Capability`, JSON on every POST, and a bounded refused-body drain. Only `GET`/`HEAD /health` is public. `packaging/freeze_entry.py` refuses a non-loopback bind. The agent skill sends the capability only to a loopback bridge. Tests port the forge-cortex cases and drive the wired app; `qualify_frozen.py` proves four refusals against the frozen binary with no audit line. Still needed: forge-neuronforge's image lane must send the capability, and the AuthorForge shell must mint it and pass it to the bridge and to NeuronForge Local.
- Scope: **open** until (1) this fix merges, (2) NeuronForge Local's image lane sends the capability, and (3) AuthorForge's pins include both and its real image path is checked against them.
- Update (2026-10-30, BDS-XMACH-CALLER-BOUNDARY-001 WP00, forge PR #325). Verified at `f308cdd` (origin/master).
  - Observed behavior: the bridge half of the fix is merged. Commit `f308cdd` (#13) adds `forgeagents-forgeimages/bridge/local_caller_boundary.py`. The middleware is wired at `forgeagents-forgeimages/bridge/forgeimages_bridge.py:94` and runs first. It refuses a non-loopback peer, a non-loopback or wrong-port `Host`, and any `Origin` with `403` (`local_caller_boundary.py:81-86`). Only `GET`/`HEAD /health` is public (`:87-92`). It refuses every other route with `503 local_capability_unconfigured` when `FORGEIMAGES_BRIDGE_CAPABILITY` is not set (`:93-96`), and with `401` when `X-AuthorForge-ForgeImages-Capability` (`:46`) is missing or wrong (`:97-101`). `packaging/freeze_entry.py:114` refuses a non-loopback bind. Condition (1) of the scope is met.
  - The "What is wrong" text above is now historical. It describes the bridge before `f308cdd`. It does not describe the bridge at `f308cdd`.
  - Documentation drift: `doc/system/14-future-work-tally.md:28` (gap G0) still says that the bridge accepts a call from any local caller, with no `Host`, `Origin` or capability check. That is false at `f308cdd`. Parts `doc/system/05-config-env.md:16`, `doc/system/06-api-layer.md:161,168` and `doc/system/12-frozen-sidecar.md:45` already describe the boundary correctly. Part 14 contradicts them.
  - Proposed correction: change G0 in part 14 to say that the bridge boundary is merged (`f308cdd`), and that the gap that stays open is the consumer side and its proof (conditions (2) and (3) below). Change the "Where" cell to `bridge/local_caller_boundary.py`. Rebuild with `bash doc/system/BUILD.sh`. This change does not edit part 14. A separate, authorized documentation change must do it.
  - Consumer side, observed only: AuthorForge `origin/main` at `467bbe37` (AuthorForge #934) pins the `forgeimages` submodule at `f308cdd` and `NEURONFORGE_PROVEN_COMMIT` at `da83d58` (forge-neuronforge #28). Its shell mints `FORGEIMAGES_BRIDGE_CAPABILITY` and gives it to the bridge and to NeuronForge Local (`src-tauri/src/infrastructure/service_manager.rs:1502,1518`). Its release smoke checks a `401` without the capability and a compile with it (`scripts/smoke-release-sidecars.py:384,403`). This entry did not verify the real AuthorForge image path (NeuronForge Local lane to the bridge) end to end, and records no independent review. Thus conditions (2) and (3) are not proven here.
  - Status: **Open — recorded, unresolved until the correction is verified.** The KI stays open until a verified check closes conditions (2) and (3), and the G0 text in part 14 is corrected.

## KI-IMG-20261017-001 — the bridge cannot compile a real raster master

- Date: 2026-10-17. Found while preparing to ship the bridge inside AuthorForge release bundles.
- What is wrong: `POST /compile/{template_id}` returned HTTP 500 for every real diffusion master. The bridge log showed `OSError: [Errno 7] Argument list too long`.
- Root cause: the bridge passed the payload to `forgeimages-cli` as the `--payload` argument. The payload carries the base64 master. A 1080×1080 PNG is about 4.6 MB of base64. Linux refuses a single argument over 128 KiB, and Windows limits the whole command line to 32 KiB. Only tiny or flat masters fit, so the fault did not show in tests that used small fixtures.
- Fix: `--payload -` reads the payload from stdin, and the bridge always uses it for `validate` and `compile`. `forgeimages-core/tests/cli_payload.rs` and `forgeagents-forgeimages/tests/test_bridge_cli_payload.py` cover both sides. A live run compiled a 4.6 MB noise master to `panel-square` and returned the PNG and the 270×270 JPEG.
- Scope: **closed** by the change that adds this file.

## KI-IMG-20261017-002 — the engine built from an unpinned dependency resolve

- Date: 2026-10-17. Found while freezing the bridge for AuthorForge release bundles.
- What is wrong: `.gitignore` excluded `Cargo.lock`. Every build of `forgeimages-cli` resolved its crate versions again, so two builds of the same commit could link different code.
- Root cause: the repository was treated as a library. It also produces a binary, and the binary now ships inside AuthorForge.
- Fix: `Cargo.lock` is tracked. `packaging/build.sh` and the freeze workflow build with `--locked`.
- Scope: **closed** by the change that tracks the lock.


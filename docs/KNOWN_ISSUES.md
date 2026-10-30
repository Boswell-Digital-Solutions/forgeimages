# ForgeImages — Known Issues

Findings for this repository: bugs, root causes, gaps, and open tracking state.
Each entry has a date, what is wrong, the root cause, the fix, and an open or closed scope.

## KI-IMG-20261030-001 — the bridge accepts a call from any local caller, a web page included

- Date: 2026-10-30. Found by a static read, recorded in AuthorForge `docs/reports/2026-10-30-support-repo-check.md` as S-2. Not reproduced against a running bridge. Priority: medium (operator ruling, 2026-10-30).
- What is wrong: `forgeagents-forgeimages/bridge/forgeimages_bridge.py` checks no `Host` header, no `Origin`, and no capability on any route. The only middleware limits the body size (`:77`). `POST /validate/{template_id}` and `POST /compile/{template_id}` run `forgeimages-cli` as a subprocess. The frozen bridge binds `127.0.0.1` (`packaging/freeze_entry.py:111`), which stops other hosts but not a page in the user's browser. A DNS-rebinding page is same-origin and can call both routes. The impact is CPU use and audit-log rows. The caller cannot name a file path, because the Six Laws keep paths off the boundary.
- Root cause: the bridge was written for agents on a trusted host, before it shipped inside AuthorForge. The AuthorForge shell passes it no capability (AuthorForge `src-tauri/src/infrastructure/service_manager.rs:1123`).
- Fix, not done: put a caller boundary in front of the app. The reference contract is forge-neuronforge `service/local_caller_boundary.py` (`LocalCallerBoundary`): one loopback `Host` with the bound port, any `Origin` refused, a per-launch capability compared in constant time. Use a governed shared implementation or an independently verified equivalent. The AuthorForge shell must mint the capability, and AuthorForge callers must send it. Required proof: negative tests, positive tests for the authorized caller, a check against the real AuthorForge caller, and an independent review.
- Scope: **open** until the fix is shown working, not when it is only documented.

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


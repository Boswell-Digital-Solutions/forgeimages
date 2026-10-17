# ForgeImages — Known Issues

Findings for this repository: bugs, root causes, gaps, and open tracking state.
Each entry has a date, what is wrong, the root cause, the fix, and an open or closed scope.

## KI-IMG-20261017-001 — the bridge cannot compile a real raster master

- Date: 2026-10-17. Found while preparing to ship the bridge inside AuthorForge release bundles.
- What is wrong: `POST /compile/{template_id}` returned HTTP 500 for every real diffusion master. The bridge log showed `OSError: [Errno 7] Argument list too long`.
- Root cause: the bridge passed the payload to `forgeimages-cli` as the `--payload` argument. The payload carries the base64 master. A 1080×1080 PNG is about 4.6 MB of base64. Linux refuses a single argument over 128 KiB, and Windows limits the whole command line to 32 KiB. Only tiny or flat masters fit, so the fault did not show in tests that used small fixtures.
- Fix: `--payload -` reads the payload from stdin, and the bridge always uses it for `validate` and `compile`. `forgeimages-core/tests/cli_payload.rs` and `forgeagents-forgeimages/tests/test_bridge_cli_payload.py` cover both sides. A live run compiled a 4.6 MB noise master to `panel-square` and returned the PNG and the 270×270 JPEG.
- Scope: **closed** by the change that adds this file.

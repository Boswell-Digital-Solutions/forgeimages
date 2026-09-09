# ForgeImages — Claude Code Context

This file provides guidance to Claude Code (claude.ai/code) when working with code in this
repository.

Template-driven deterministic image-asset validation and compilation with audit manifests.
Rust core engine + CLI (`forgeimages-core/`), Python agent bridge and skill
(`forgeagents-forgeimages/`).

Canonical reference: `doc/system/` (`bash doc/system/BUILD.sh`).

---

## The Six Laws (non-negotiable)

1. **SVG is truth** — vector masters are canonical; raster exports derive from them.
2. **Templates are contracts** — old templates work forever. Bump the version; never modify one in
   place.
3. **Validation is protective** — it catches errors before they propagate.
4. **Deterministic output** — same inputs, same outputs, always.
5. **Manifests enable reproduction** — SHA-256 hashes link inputs to outputs.
6. **Agents suggest, the engine enforces** — all validation and compilation go through templates.

Enforcement invariants, proven by `forgeimages-core/tests/invariants.rs` and
`forgeagents-forgeimages/tests/test_agent_boundary.py`:

- `compile_asset()` **always** calls `validate_asset()`. Never add a path that skips it.
- HTTP 422 = validation failure; agents cannot proceed past it. **CLI exit code 2 = validation
  failure, and the bridge depends on that exact code** — do not change it.
- The audit log is append-only. Never modify, truncate, or delete.
- **No file paths cross the trust boundary** — all data is base64. Agents never write files
  directly and never reach the engine except through skill → bridge → CLI.

Agents may generate candidates, select candidates, request compilation, and list templates. They
may not skip validation, override templates, write files, or change the failure mode.

---

## Verification

```bash
cd forgeimages-core && cargo test          # includes the 6 contract invariants
cd forgeagents-forgeimages && pytest tests/ -v
```

`cargo test --test invariants` narrows to the contract invariants alone.

---

## Non-obvious

- **Rules and policy are separate:** rules emit `ValidationViolation` structs; the validator then
  applies the failure mode (Block / Warn / Log). Do not fold the decision into a rule.
- All JSON is canonicalized (sorted keys, no whitespace) before hashing, so SHA-256 is stable
  across platforms.
- Templates carry semver, and the engine checks `engineMinVersion` against `ENGINE_VERSION`.

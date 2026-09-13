# ForgeImages Cloud Image Fulfillment — Slice 01 Evidence

**Schema:** `bds.forgeimages-cloud-fulfillment-evidence.v1`

**Source revision:** `11a5413` (`origin/master` at branch creation)

**Observed:** 2026-09-13

**Authority:** ForgeImages owns deterministic production validation contracts;
NeuroForge remains the cloud-generation and fulfillment-saga owner.

## Implemented

- strict `forgeimages_validation_request.v1` transport model
- strict `forgeimages_validation_result.v1` transport model
- candidate artifact, rejected artifact, and compiled-asset summary records
- 15 stable rejection codes and soft/hard failure severity
- fail-closed schema, enum, timestamp, extra-field, and result-count validation
- JSON round-trip and generation-dependency boundary tests

## Verification

- Slice 01 focused Python tests: 18 passed
- Full ForgeImages Python bridge suite: 36 passed
- ForgeImages core Rust tests: 48 passed
- Live JSON round-trip through ForgeImages and NeuroForge v1 models: passed
- Ruff lint and format checks for changed Python surfaces: passed
- Canonical `doc/IMASYSTEM.md` rebuild and snapshot validation: passed
- Diff whitespace check: passed

## Known boundary

This slice adds contracts only. It does not add a validation endpoint, invoke
the validator/compiler for these payloads, build manifests, call NeuroForge, or
include any cloud generation provider logic. Slice 02 owns deterministic
validator and manifest integration.

The repository's pre-existing Python settings model emits one Pydantic v2
deprecation warning. Strict `cargo clippy -D warnings` is also blocked by eight
pre-existing lints in unmodified Rust core files; `cargo test`, `cargo fmt
--check`, and the changed Python lint/type checks pass.

## Human action

Review the mirrored field names and service identity locks before merge. No
semantic contract expansion should be accepted without a new schema version.

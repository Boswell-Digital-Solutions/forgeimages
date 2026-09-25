# §3 — Tech Stack

## Rust Core Engine

| Dependency | Version | Purpose |
|------------|---------|---------|
| serde | 1.0 (features: derive) | Serialization/deserialization |
| serde_json | 1.0 | JSON parsing and canonical output |
| sha2 | 0.10 | SHA-256 manifest hashing |
| semver | 1.0 (features: serde) | Template version compatibility |
| thiserror | 1.0 | Typed error handling |
| base64 | 0.21 | Export data encoding |
| chrono | 0.4 (features: serde) | Timestamps |
| uuid | 1.0 (features: v4, serde) | Asset and export IDs |
| clap | 4.0 (features: derive) | CLI argument parsing |
| tempfile | 3.0 (dev only) | Test fixtures |

**Rust edition:** 2024
**MSRV:** Follows Rust 2024 edition requirements

## Python Bridge + Skill

| Dependency | Version | Purpose |
|------------|---------|---------|
| fastapi | >=0.104.0 | HTTP bridge framework |
| uvicorn[standard] | >=0.24.0 | ASGI server |
| pydantic | >=2.5.0 | Request/response validation |
| pydantic-settings | >=2.1.0 | Environment-based configuration |
| httpx | >=0.25.0 | Async HTTP client (skill → bridge) |
| pytest | >=7.4.0 (dev) | Test framework |
| pytest-asyncio | >=0.21.0 (dev) | Async test support |

**Python version:** >=3.10
**Build system:** hatchling

## Build Tools

| Tool | Purpose |
|------|---------|
| cargo | Rust build + test |
| pip / hatch | Python package management |
| uvicorn | Bridge server |
| pytest | Python tests |

## Feature Flags

| Flag | Purpose |
|------|---------|
| `test-hooks` | Enables test hook points in compilation pipeline |

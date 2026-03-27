# ADR-001: Polyglot Monorepo Structure

**Date:** 2026-03-26
**Status:** Accepted

## Context

polyarchos must demonstrate mastery across Rust, TypeScript, Python, and WASM simultaneously.
The platform has four distinct deployable units (core-api, rag-engine, graph-service, frontend)
plus a WASM library, shared domain types, proto contracts, and infrastructure manifests.

The primary question is whether to organise these as separate repositories or a single monorepo.

## Decision

Use a single polyglot monorepo with per-language workspace tooling:
- Rust: Cargo workspace (`Cargo.toml` at root, `members` list)
- Python: uv workspace (`pyproject.toml` at root, `[tool.uv.workspace]`)
- Node: npm workspaces (`package.json` at root, `workspaces` array)

Proto definitions live in `proto/` at the root and are shared across all services via `buf generate`.
A shared Rust library crate (`crates/domain/`) holds AUTOSAR domain types used by both `core-api`
and `wasm/`.

## Rationale

**Monorepo advantages for this project:**
- Atomic commits across service + proto + infra changes (no cross-repo version pinning)
- Single CI pipeline with cross-language visibility
- Shared domain types without a separate package registry
- Demonstrates polyglot monorepo ownership — an explicit preferred qualification in the target JD

**Why not separate repos:**
- Cross-repo proto versioning adds overhead with no benefit at this scale
- Splitting the Rust domain crate would require publishing to crates.io just to share types
- The portfolio signal is weaker: separate repos read as separate projects

**Why per-language workspace tooling (not Nx/Bazel):**
- Each language's native tooling (Cargo, uv, npm) is what the JD specifically references
- Adds no unfamiliar build abstraction layer
- Nx/Bazel would be appropriate at 20+ services; premature here

## Consequences

- All developers need Rust (rustup), Python 3.12+ (uv), Node 20+, buf, and wasm-pack installed
- `docs/onboarding.md` must document the full prerequisite list
- CI installs all four toolchains; total pipeline time is higher than a single-language project
- Adding a new language to the monorepo requires adding its workspace manifest to the root

## References

- [Cargo workspaces](https://doc.rust-lang.org/cargo/reference/workspaces.html)
- [uv workspaces](https://docs.astral.sh/uv/concepts/workspaces/)
- [npm workspaces](https://docs.npmjs.com/cli/v10/using-npm/workspaces)

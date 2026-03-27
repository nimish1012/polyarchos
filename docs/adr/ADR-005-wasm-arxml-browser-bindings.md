# ADR-005: WASM ARXML Browser Bindings

**Date:** 2026-03-27
**Status:** Accepted

## Context

The frontend needs to parse and validate ARXML fragments in the browser — for example, to give
inline feedback as a user pastes ARXML into a configuration form, or to preview port-connection
compatibility before sending data to the backend.

ARXML is XML-based and can be large. Options considered:

1. **Send ARXML to the backend for parsing** — introduces round-trip latency and requires the
   backend to be reachable; not suitable for offline-first tooling.
2. **Reimplement parsing in TypeScript** — duplicates domain logic; divergence risk is high because
   the authoritative domain types already live in `crates/domain`.
3. **Compile `crates/domain` to WASM** — reuses the existing Rust domain types with zero
   duplication, runs offline in the browser, and wasm-bindgen generates TypeScript `.d.ts`
   declarations automatically.

## Decision

Compile AUTOSAR domain logic to WebAssembly via `wasm-bindgen` in the `wasm/` crate. Expose the
following browser-callable functions:

| Function | Input | Output |
|---|---|---|
| `parse_arxml_component` | ARXML XML string | `{ component, ports }` JSON |
| `validate_component` | `SoftwareComponent` JSON | `void` or throws |
| `classify_variant` | ARXML short-name path | `"classic"` or `"adaptive"` |
| `resolve_port_connections` | `Port[]` JSON | `[Port, Port][]` JSON |

The `wasm/` crate depends on `crates/domain` (shared domain types) and adds:

- `roxmltree` — pure-Rust, zero-dependency XML parser; compiles cleanly to `wasm32-unknown-unknown`.
- `console_error_panic_hook` — routes Rust panics to `console.error` for browser devtools.

Build artefacts land in `wasm/pkg/` (gitignored; generated at CI time) and are consumed by the
frontend as a local ES module.

## Rationale

- **No duplication**: domain types (`SoftwareComponent`, `Port`, `AutosarVariant`) are defined once
  in `crates/domain` and used by both the Rust backend and the WASM module.
- **Offline capability**: ARXML parsing runs entirely in the browser; no network call required.
  Consistent with the project-wide offline-inference constraint.
- **Type safety**: wasm-bindgen generates TypeScript `.d.ts` declarations from Rust doc-comments
  automatically, giving the frontend compile-time types.
- `roxmltree` was chosen over `quick-xml` for its DOM-style API, which maps naturally to ARXML's
  deeply nested `AR-PACKAGE` hierarchy.

## Consequences

- **Positive**: Single source of truth for domain types. Frontend gets validated ARXML data without
  a server round-trip.
- **Positive**: WASM binary is ~163 KB optimised — acceptable for a desktop engineering tool.
- **Negative**: Build requires the `wasm32-unknown-unknown` Rust target and `wasm-pack`.
  Added to CI pipeline (step 5) and documented in CLAUDE.md.
- **Negative**: wasm-opt bundled with older wasm-pack versions does not recognise
  `memory.copy`/`memory.fill` (bulk-memory proposal). Workaround: pass `--enable-bulk-memory` via
  `[package.metadata.wasm-pack.profile.release]` in `wasm/Cargo.toml`.
- **Out of scope**: The WASM module is a pure library — no network calls, no side effects. It does
  not replace the backend; it only provides client-side preview/validation.

## References

- [wasm-bindgen book](https://rustwasm.github.io/wasm-bindgen/)
- [roxmltree crate](https://crates.io/crates/roxmltree)
- AUTOSAR Classic ARXML schema — `AR-PACKAGE`, `APPLICATION-SW-COMPONENT-TYPE`, `P-PORT-PROTOTYPE`

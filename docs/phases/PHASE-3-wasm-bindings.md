# Phase 3 — WASM Bindings

**Date completed:** 2026-03-27
**Branch:** master

---

## Goal

Compile AUTOSAR domain logic to WebAssembly so the React frontend can parse and validate ARXML
fragments entirely in the browser, without a network round-trip.

---

## Prerequisites installed

| Tool | Version | Install command |
|---|---|---|
| `wasm32-unknown-unknown` target | (rustup) | `rustup target add wasm32-unknown-unknown` |
| `wasm-pack` | latest | `cargo install wasm-pack` |

---

## Files created / modified

### `wasm/Cargo.toml` — modified

Added dependencies:

```toml
roxmltree = "0.19"                  # pure-Rust DOM XML parser
console_error_panic_hook = "0.1"    # browser-friendly panic messages

[package.metadata.wasm-pack.profile.release]
wasm-opt = ["--enable-bulk-memory", "-O"]
```

The `wasm-opt` metadata is required because the wasm-opt binary bundled with older wasm-pack
releases does not recognise `memory.copy`/`memory.fill` instructions emitted by Rust. Passing
`--enable-bulk-memory` enables the bulk-memory proposal in the validator.

### `wasm/src/lib.rs` — rewritten

All `#[wasm_bindgen]` public exports:

| Export | Signature | Description |
|---|---|---|
| `module_init` | `() -> ()` | `#[wasm_bindgen(start)]` — installs panic hook |
| `version` | `() -> String` | Returns crate version for load verification |
| `parse_arxml_component` | `(&str) -> Result<JsValue, JsError>` | Parses ARXML XML, returns `{component, ports}` JSON |
| `validate_component` | `(&str) -> Result<(), JsError>` | Validates `SoftwareComponent` JSON |
| `classify_variant` | `(&str) -> String` | Classifies ARXML path as `"classic"` or `"adaptive"` |
| `resolve_port_connections` | `(&str) -> Result<JsValue, JsError>` | Returns compatible `[provided, required]` port pairs |

Error handling: all fallible functions return `JsError` (not `JsValue`) so callers can use standard
`try/catch`. Panics are eliminated from all exported paths.

### `wasm/src/arxml.rs` — new

Internal helpers (not exported to JS):

- `variant_from_tag(tag)` — maps ARXML element names to `AutosarVariant`
- `find_swc_node(doc)` — finds first SWC element in a parsed document
- `build_arxml_path(node, name)` — walks `AR-PACKAGE` ancestors to build `/Pkg/Sub/Name` path
- `parse_ports(node, path)` — extracts `P-PORT-PROTOTYPE` and `R-PORT-PROTOTYPE` children
- `validate_swc(component)` — returns `Vec<String>` of validation errors

Supported Classic SWC tags: `APPLICATION-SW-COMPONENT-TYPE`, `SENSOR-ACTUATOR-SW-COMPONENT-TYPE`,
`COMPLEX-DEVICE-DRIVER-SW-COMPONENT-TYPE`, `ECU-ABSTRACTION-SW-COMPONENT-TYPE`,
`SERVICE-SW-COMPONENT-TYPE`.

Supported Adaptive SWC tags: `ADAPTIVE-APPLICATION-SW-COMPONENT-TYPE`.

### `wasm/src/ports.rs` — new

- `find_compatible_pairs(ports)` — returns `Vec<(Port, Port)>` of (provided, required) pairs
  sharing the same `interface_ref`. Normalises order so `provided` is always first.

---

## Architecture decision

ADR-005 (`docs/adr/ADR-005-wasm-arxml-browser-bindings.md`) documents the rationale for WASM over
TypeScript reimplementation or server-side parsing.

---

## Build output

```
wasm/pkg/
├── polyarchos_wasm.js          # ES module loader
├── polyarchos_wasm.d.ts        # TypeScript declarations (auto-generated)
├── polyarchos_wasm_bg.wasm     # Optimised WASM binary (~163 KB)
├── polyarchos_wasm_bg.wasm.d.ts
└── package.json
```

`wasm/pkg/` is gitignored — generated at build time by `wasm-pack build wasm/ --target web`.

---

## Test results

**Host-target unit tests** (`cargo test -p polyarchos-wasm`): **16/16 passed**

```
test arxml::tests::variant_from_tag_classic           ... ok
test arxml::tests::variant_from_tag_adaptive          ... ok
test arxml::tests::variant_from_tag_unknown           ... ok
test arxml::tests::validate_swc_valid                 ... ok
test arxml::tests::validate_swc_empty_name            ... ok
test arxml::tests::validate_swc_relative_path         ... ok
test arxml::tests::find_swc_parses_classic            ... ok
test arxml::tests::build_arxml_path_nested_packages   ... ok
test arxml::tests::parse_ports_extracts_provided_and_required ... ok
test ports::tests::finds_matching_provided_required_pair      ... ok
test ports::tests::ignores_mismatched_interface               ... ok
test ports::tests::ignores_same_direction_same_interface      ... ok
test ports::tests::normalises_required_provided_order         ... ok
test tests::version_is_nonempty                       ... ok
test tests::classify_variant_adaptive                 ... ok
test tests::classify_variant_classic                  ... ok
```

**WASM build** (`wasm-pack build wasm/ --target web`): success, 163 KB optimised binary.

**TypeScript declarations generated** at `wasm/pkg/polyarchos_wasm.d.ts` — all 5 exported
functions present.

---

## What's stubbed / deferred

- **Browser integration tests** (`wasm-pack test --headless --chrome`): deferred to Phase 5
  (Frontend) when the React app can import `wasm/pkg/` and exercise the functions end-to-end.
- **Adaptive ARXML fixtures**: only Classic SWC ARXML tested in unit tests. Adaptive fixtures
  will be added in `tests/fixtures/` during Phase 5.
- `classify_variant` uses a path heuristic (`/Adaptive/` segment). A more robust approach based
  on actual ARXML schema would be a future improvement.

---

## Next phase

**Phase 4 — Python RAG Engine** (`services/rag-engine/`):
- ARXML ingestion pipeline with schema-aware XML parsing
- Local embedding model (fastembed) for vector generation
- Milvus ingestion + similarity search
- Neo4j graph population from SWC/Port relationships
- RAG query endpoint over gRPC

# Phase 5 — React + TypeScript Frontend Dashboard

## Overview

Phase 5 delivers the browser-based dashboard for the polyarchos platform. It provides four
interactive pages backed by the core-api REST API plus in-browser WASM parsing.

## Deliverables

### Toolchain

| Tool | Version | Purpose |
|---|---|---|
| Vite | 5.x | Bundler + dev server |
| React | 18.x | UI framework |
| TypeScript | 5.x | Strict mode (`strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`) |
| TanStack Query | 5.x | Server state (see ADR-009) |
| Zustand | 4.x | Client state (see ADR-009) |
| Zod | 3.x | Runtime schema validation for API responses |
| React Router | 6.x | Client-side routing |
| Vitest | 2.x | Unit + component tests |
| @testing-library/react | 16.x | Component rendering helpers |
| vite-plugin-wasm | 3.x | WASM ES module support |
| vite-plugin-top-level-await | 1.x | Enables top-level await for WASM init |

### Pages

| Route | Component | Description |
|---|---|---|
| `/components` | `ComponentBrowser` | Paginated, filterable table of all SWCs |
| `/graph` | `GraphExplorer` | SVG radial-layout graph; Phase 6 will add Neo4j edges |
| `/search` | `SemanticSearch` | Natural-language Q&A backed by rag-engine |
| `/validate` | `ArxmlValidator` | In-browser ARXML parsing via WASM module |
| `/playground` | `ApiPlayground` | Dev-facing REST request builder |

### Architecture

```
frontend/src/
├── api/
│   ├── schema.ts      # Zod schemas derived from core-api OpenAPI types
│   └── client.ts      # Typed fetch wrappers; ApiError for non-2xx responses
├── store/
│   └── ui.ts          # Zustand store (selectedComponentId, variantFilter, searchHistory)
├── wasm/
│   └── loader.ts      # Dynamic WASM import with graceful fallback
├── components/
│   ├── ErrorBoundary.tsx   # Route-level error boundary
│   ├── LoadingSpinner.tsx  # Accessible loading indicator
│   ├── NavBar.tsx          # Top navigation with active-link highlighting
│   └── VariantBadge.tsx    # Classic / Adaptive pill badge
├── pages/             # One component per route (see table above)
├── styles/
│   └── index.css      # Dark-themed design tokens + component styles
├── App.tsx            # Route tree + QueryClientProvider + BrowserRouter
└── main.tsx           # ReactDOM.createRoot entry point
```

### API Types

All API types are derived from the Zod schemas in `schema.ts`, which mirror the utoipa-generated
OpenAPI types from `services/core-api/src/rest/types.rs`. No hand-written duplicates exist.
Runtime validation is performed on every API response via `schema.safeParse()`.

### WASM Integration

The Phase 3 WASM module is loaded lazily on the ArxmlValidator page. The loader (`loader.ts`)
returns a discriminated union `LoadResult`:
- `{ status: 'loaded', module: WasmModule }` — happy path
- `{ status: 'unavailable', reason: string }` — WASM binary not built yet

The page degrades gracefully and shows a build instruction banner when the WASM binary is absent.

### State Management

See ADR-009. Server state (component lists, search results) is owned by TanStack Query.
Client state (selected node, active filter, search history) is owned by Zustand.

## Tests

| File | Tests |
|---|---|
| `__tests__/schema.test.ts` | Zod schema parsing, invalid variant, missing fields, score range |
| `__tests__/ComponentBrowser.test.tsx` | Loading, data render, error banner, pagination, filter |
| `__tests__/ArxmlValidator.test.tsx` | WASM load states, parse success, parse error |

Run with:

```bash
npm run test -w frontend
npm run typecheck -w frontend
```

## Build Verification

```bash
cd frontend && npm install
npm run typecheck   # tsc --noEmit — must pass with zero errors
npm run test        # vitest run
npm run build       # tsc -b && vite build
```

## Phase 6 Notes

- `GraphExplorer` currently shows only nodes in a static radial layout. Phase 6 will wire
  `graph-service` (Neo4j) to core-api and draw port-connection edges between SWC nodes.
- The Phase 6 `SemanticSearch` will be connected to the live rag-engine gRPC endpoint.

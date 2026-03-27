# ADR-009: Frontend State Management — TanStack Query + Zustand Split

**Date:** 2026-03-27
**Status:** Accepted

## Context

The polyarchos frontend has two distinct categories of state:

1. **Server state** — data fetched from core-api (component lists, search results). This data has
   a lifecycle tied to the server: it can become stale, needs background re-fetching, and benefits
   from caching and deduplication.

2. **Client state** — ephemeral UI state that has no server representation (selected component ID,
   active variant filter, search history). This state is owned entirely by the browser session.

Mixing both categories into a single store (e.g., Redux) creates accidental complexity: cache
invalidation logic entangles with selection state, and loading/error states must be hand-managed.

## Decision

Use **TanStack Query v5** for all server state and **Zustand v4** for all client state.

- `useQuery` / `useMutation` handle all API calls. No `useEffect` + `useState` data fetching.
- The Zustand `useUiStore` holds `selectedComponentId`, `variantFilter`, and `searchHistory`.
- Components read server data via TanStack Query hooks and UI state via Zustand hooks. The two
  concerns never share a store.

## Rationale

- TanStack Query provides automatic background re-fetching, deduplication of in-flight requests,
  cache lifetime control (`staleTime`), and typed loading/error states — all concerns that a
  hand-rolled store would need to re-implement.
- Zustand is minimal (≈1 kB), requires no boilerplate, and supports `immer`-style updates if
  needed later. It does not penalise simple cases.
- Separating the two categories makes it immediately obvious where any piece of state lives, which
  reduces cognitive overhead during future maintenance.
- No Redux / Context API for server state: both require manual cache management and produce
  excessive re-renders without careful memoisation.

## Consequences

- **Positive:** Clean separation of concerns. Loading/error/stale states are handled declaratively.
  Background re-fetching is automatic.
- **Positive:** TanStack Query DevTools can be added in development for cache inspection without
  any code changes to pages.
- **Negative:** Developers unfamiliar with TanStack Query need to learn its concepts (query keys,
  stale time, mutations vs queries).
- **Negative:** Zustand's lack of enforced structure means discipline is required not to conflate
  server-derived data into the UI store.

## References

- [TanStack Query v5 docs](https://tanstack.com/query/v5/docs/framework/react/overview)
- [Zustand repo](https://github.com/pmndrs/zustand)
- ADR-010 (future): real-time updates via WebSocket — may introduce a third state category

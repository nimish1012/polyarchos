# ADR-004: Dual-Server gRPC + REST Architecture

**Date:** 2026-03-26
**Status:** Accepted

## Context

core-api must expose both gRPC (must skill) and REST (must skill) from a single Rust binary.
The options were: a single multiplexed server, two separate servers, or a gRPC-gateway proxy.

## Decision

Run two servers concurrently in the same process via `tokio::try_join!`:
- gRPC on `:50051` — tonic `ComponentServiceServer`
- REST on `:8080` — axum router with utoipa OpenAPI annotations

Both share the same `ComponentStore` (wrapped in `Arc<RwLock>`) with zero copying.
Proto-generated types are mapped to domain types at the gRPC boundary.
REST types are defined separately in `rest/types.rs` and mapped from domain types in handlers.

## Rationale

**Why not gRPC-gateway (proto → REST transcoding):**
- utoipa generates richer, more idiomatic OpenAPI docs (explicit schema names, descriptions)
- REST handlers can diverge from gRPC in shape (pagination tokens, HTTP caching, partial updates)
- No runtime proxy process; lower operational complexity

**Why not a single HTTP/2 multiplexed server:**
- tonic + axum multiplexing on one port adds routing complexity
- Separate ports make firewall rules, Kubernetes Services, and load balancer config cleaner
- Standard in production: gRPC for internal service-to-service, REST for external/frontend clients

**Why `tokio::try_join!`:**
- If either server dies, the entire process exits — fail-fast, no silent half-broken state
- Single process = single Kubernetes pod, single health check endpoint, single log stream

## Consequences

- Two Kubernetes Service definitions needed (one per port)
- CI smoke test must check both ports independently
- OpenAPI spec (utoipa) and gRPC reflection serve as the two independent API discovery surfaces
- `protoc-bin-vendored` build dependency eliminates the need for a system `protoc` install

## References

- ADR-003: Proto-first API design
- [tonic + axum dual server example](https://github.com/hyperium/tonic/tree/master/examples)

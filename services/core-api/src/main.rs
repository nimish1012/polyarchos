//! polyarchos core-api — dual gRPC + REST gateway.
//!
//! Starts two servers concurrently:
//! - gRPC on `CORE_API_GRPC_PORT` (default 50051) via tonic
//! - REST on `CORE_API_REST_PORT` (default 8080) via axum
//!
//! Both servers share the same `ComponentStore` via `Arc`.

#![deny(clippy::all)]
#![deny(clippy::pedantic)]

mod config;
mod error;
mod grpc;
mod rest;
mod store;

use anyhow::Result;
use tower_http::trace::TraceLayer;
use tracing::info;
use tracing_subscriber::{fmt, prelude::*, EnvFilter};

use grpc::proto::component_service_server::ComponentServiceServer;
use grpc::GrpcComponentService;
use store::ComponentStore;

#[tokio::main]
async fn main() -> Result<()> {
    // ── Observability ─────────────────────────────────────────────────────────
    tracing_subscriber::registry()
        .with(EnvFilter::try_from_default_env().unwrap_or_else(|_| "info".into()))
        .with(fmt::layer().json())
        .init();

    // ── Config ────────────────────────────────────────────────────────────────
    let cfg = config::Config::from_env();
    info!(
        grpc_addr = %cfg.grpc_addr,
        rest_addr = %cfg.rest_addr,
        version = env!("CARGO_PKG_VERSION"),
        "core-api starting",
    );

    // ── Shared state ──────────────────────────────────────────────────────────
    let store = ComponentStore::new();
    store.seed_fixtures(); // synthetic fixtures for local dev
    info!(count = store.count(), "seeded component store");

    // ── gRPC server ───────────────────────────────────────────────────────────
    let grpc_service = GrpcComponentService::new(store.clone());
    let grpc_server = tonic::transport::Server::builder()
        .add_service(ComponentServiceServer::new(grpc_service))
        .serve(cfg.grpc_addr);

    // ── REST server ───────────────────────────────────────────────────────────
    let rest_app = rest::router(store).layer(TraceLayer::new_for_http());
    let rest_listener = tokio::net::TcpListener::bind(cfg.rest_addr).await?;
    let rest_server = axum::serve(rest_listener, rest_app);

    info!("gRPC listening on {}", cfg.grpc_addr);
    info!("REST listening on {}", cfg.rest_addr);
    info!("Swagger UI at http://{}/swagger-ui/", cfg.rest_addr);

    // ── Run both servers concurrently ─────────────────────────────────────────
    tokio::try_join!(
        async { grpc_server.await.map_err(anyhow::Error::from) },
        async { rest_server.await.map_err(anyhow::Error::from) },
    )?;

    Ok(())
}

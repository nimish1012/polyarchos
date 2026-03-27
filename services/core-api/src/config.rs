//! Configuration loaded from environment variables.

use std::net::SocketAddr;

/// Runtime configuration for core-api.
#[derive(Debug, Clone)]
pub struct Config {
    /// Address for the gRPC server (default: 0.0.0.0:50051).
    pub grpc_addr: SocketAddr,
    /// Address for the REST server (default: 0.0.0.0:8080).
    pub rest_addr: SocketAddr,
}

impl Config {
    /// Load configuration from environment variables.
    ///
    /// Falls back to sensible local-dev defaults when variables are absent.
    pub fn from_env() -> Self {
        let grpc_port: u16 = std::env::var("CORE_API_GRPC_PORT")
            .ok()
            .and_then(|v| v.parse().ok())
            .unwrap_or(50051);

        let rest_port: u16 = std::env::var("CORE_API_REST_PORT")
            .ok()
            .and_then(|v| v.parse().ok())
            .unwrap_or(8080);

        Self {
            grpc_addr: SocketAddr::from(([0, 0, 0, 0], grpc_port)),
            rest_addr: SocketAddr::from(([0, 0, 0, 0], rest_port)),
        }
    }
}

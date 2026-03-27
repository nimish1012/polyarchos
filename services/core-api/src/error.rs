//! Unified error type for core-api.
//!
//! `AppError` implements both `IntoResponse` (axum REST) and
//! converts to `tonic::Status` (gRPC) so handlers stay error-type-agnostic.

use axum::{http::StatusCode, response::IntoResponse, Json};
use serde_json::json;

/// Application-level errors surfaced by both REST and gRPC handlers.
#[derive(Debug, thiserror::Error)]
pub enum AppError {
    /// The requested resource does not exist.
    #[error("not found: {0}")]
    NotFound(String),

    /// The request payload is malformed or violates a domain constraint.
    #[error("invalid request: {0}")]
    InvalidRequest(String),

    /// An unexpected internal failure occurred.
    #[error("internal error: {0}")]
    Internal(#[from] anyhow::Error),
}

impl IntoResponse for AppError {
    fn into_response(self) -> axum::response::Response {
        let (status, message) = match &self {
            AppError::NotFound(msg) => (StatusCode::NOT_FOUND, msg.clone()),
            AppError::InvalidRequest(msg) => (StatusCode::BAD_REQUEST, msg.clone()),
            AppError::Internal(err) => {
                tracing::error!("internal error: {err:#}");
                (StatusCode::INTERNAL_SERVER_ERROR, "internal server error".to_owned())
            }
        };
        (status, Json(json!({ "error": message }))).into_response()
    }
}

impl From<AppError> for tonic::Status {
    fn from(err: AppError) -> Self {
        match err {
            AppError::NotFound(msg) => tonic::Status::not_found(msg),
            AppError::InvalidRequest(msg) => tonic::Status::invalid_argument(msg),
            AppError::Internal(err) => tonic::Status::internal(err.to_string()),
        }
    }
}

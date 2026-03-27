//! REST request/response types with utoipa schema derivations.
//!
//! These are separate from both proto-generated types and domain types.
//! They form the public REST API contract documented in the OpenAPI spec.

use serde::{Deserialize, Serialize};
use utoipa::{IntoParams, ToSchema};

/// AUTOSAR platform variant.
#[derive(Debug, Clone, Serialize, Deserialize, ToSchema)]
#[serde(rename_all = "snake_case")]
pub enum AutosarVariant {
    Classic,
    Adaptive,
}

/// A software component record returned by the REST API.
#[derive(Debug, Clone, Serialize, Deserialize, ToSchema)]
pub struct ComponentResponse {
    /// Server-assigned UUID.
    pub id: String,
    /// Fully-qualified ARXML short-name path.
    pub arxml_ref: String,
    /// Human-readable component name.
    pub name: String,
    /// AUTOSAR platform variant.
    pub variant: AutosarVariant,
    /// Optional description.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
}

/// Paginated list of components.
#[derive(Debug, Serialize, Deserialize, ToSchema)]
pub struct ListComponentsResponse {
    pub components: Vec<ComponentResponse>,
    /// Token for the next page; absent on the last page.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub next_page_token: Option<String>,
    /// Total number of matching records.
    pub total_count: i64,
}

/// Query parameters for listing components.
#[derive(Debug, Deserialize, ToSchema, IntoParams)]
pub struct ListComponentsQuery {
    /// Maximum results per page (default 50, max 200).
    pub page_size: Option<i32>,
    /// Pagination token from a previous response.
    pub page_token: Option<String>,
    /// Filter by AUTOSAR variant.
    pub variant: Option<AutosarVariant>,
}

/// Request body for semantic search.
#[derive(Debug, Deserialize, ToSchema)]
pub struct SearchRequest {
    /// Natural-language search query.
    pub query: String,
    /// Maximum results to return (default 10, max 50).
    pub top_k: Option<i32>,
}

/// A single search result with relevance score.
#[derive(Debug, Serialize, Deserialize, ToSchema)]
pub struct SearchResultResponse {
    pub component: ComponentResponse,
    /// Cosine similarity score in \[0, 1\].
    pub score: f32,
}

/// Ranked search results.
#[derive(Debug, Serialize, Deserialize, ToSchema)]
pub struct SearchResponse {
    pub results: Vec<SearchResultResponse>,
}

/// Generic error response body.
#[derive(Debug, Serialize, Deserialize, ToSchema)]
pub struct ErrorResponse {
    pub error: String,
}

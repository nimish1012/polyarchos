//! axum REST handlers for the component API.

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    Json,
};
use tracing::instrument;

use crate::{error::AppError, store::ComponentStore};
use super::types::{
    AutosarVariant, ComponentResponse, ListComponentsQuery, ListComponentsResponse,
    SearchRequest, SearchResponse, SearchResultResponse,
};

// ── GET /api/v1/components/:id ────────────────────────────────────────────────

/// Get a single component by ID.
#[utoipa::path(
    get,
    path = "/api/v1/components/{id}",
    params(("id" = String, Path, description = "Server-assigned component UUID")),
    responses(
        (status = 200, description = "Component found", body = ComponentResponse),
        (status = 404, description = "Component not found"),
    ),
    tag = "components"
)]
#[instrument(skip(store))]
pub async fn get_component(
    State(store): State<ComponentStore>,
    Path(id): Path<String>,
) -> Result<Json<ComponentResponse>, AppError> {
    let stored = store
        .get(&id)
        .ok_or_else(|| AppError::NotFound(format!("component '{id}' not found")))?;

    Ok(Json(to_response(&stored.id, &stored.component)))
}

// ── GET /api/v1/components ────────────────────────────────────────────────────

/// List components with optional variant filter and pagination.
#[utoipa::path(
    get,
    path = "/api/v1/components",
    params(ListComponentsQuery),
    responses(
        (status = 200, description = "Paginated component list", body = ListComponentsResponse),
    ),
    tag = "components"
)]
#[instrument(skip(store))]
pub async fn list_components(
    State(store): State<ComponentStore>,
    Query(q): Query<ListComponentsQuery>,
) -> Json<ListComponentsResponse> {
    let variant_filter = q.variant.map(|v| match v {
        AutosarVariant::Classic => domain::swc::AutosarVariant::Classic,
        AutosarVariant::Adaptive => domain::swc::AutosarVariant::Adaptive,
    });

    let page_size = q.page_size.unwrap_or(50).clamp(1, 200) as usize;
    let offset: usize = q.page_token.as_deref().and_then(|t| t.parse().ok()).unwrap_or(0);

    let mut all = store.list(variant_filter);
    let total_count = all.len() as i64;
    all.sort_by(|a, b| a.id.cmp(&b.id));

    let page: Vec<_> = all.iter().skip(offset).take(page_size).collect();
    let next_page_token = if offset + page_size < all.len() {
        Some((offset + page_size).to_string())
    } else {
        None
    };

    Json(ListComponentsResponse {
        components: page.iter().map(|s| to_response(&s.id, &s.component)).collect(),
        next_page_token,
        total_count,
    })
}

// ── POST /api/v1/components/search ───────────────────────────────────────────

/// Semantic search over components (stub until Phase 4).
#[utoipa::path(
    post,
    path = "/api/v1/components/search",
    request_body = SearchRequest,
    responses(
        (status = 200, description = "Search results", body = SearchResponse),
        (status = 400, description = "Invalid request"),
    ),
    tag = "components"
)]
#[instrument(skip(store))]
pub async fn search_components(
    State(store): State<ComponentStore>,
    Json(req): Json<SearchRequest>,
) -> Result<Json<SearchResponse>, AppError> {
    if req.query.trim().is_empty() {
        return Err(AppError::InvalidRequest("query must not be empty".to_owned()));
    }

    let top_k = req.top_k.unwrap_or(10).clamp(1, 50) as usize;
    let query = req.query.to_lowercase();

    // TODO Phase 4: replace with Milvus vector search via rag-engine.
    let results: Vec<SearchResultResponse> = store
        .list(None)
        .into_iter()
        .filter(|s| {
            s.component.name.to_lowercase().contains(&query)
                || s.component
                    .description
                    .as_deref()
                    .unwrap_or("")
                    .to_lowercase()
                    .contains(&query)
        })
        .take(top_k)
        .map(|s| SearchResultResponse {
            component: to_response(&s.id, &s.component),
            score: 1.0,
        })
        .collect();

    Ok(Json(SearchResponse { results }))
}

// ── DELETE /api/v1/components/:id ─────────────────────────────────────────────

/// Delete a component by ID.
#[utoipa::path(
    delete,
    path = "/api/v1/components/{id}",
    params(("id" = String, Path, description = "Server-assigned component UUID")),
    responses(
        (status = 204, description = "Component deleted"),
        (status = 404, description = "Component not found"),
    ),
    tag = "components"
)]
#[instrument(skip(store))]
pub async fn delete_component(
    State(store): State<ComponentStore>,
    Path(id): Path<String>,
) -> Result<StatusCode, AppError> {
    if store.delete(&id) {
        Ok(StatusCode::NO_CONTENT)
    } else {
        Err(AppError::NotFound(format!("component '{id}' not found")))
    }
}

// ── Mapping helper ────────────────────────────────────────────────────────────

fn to_response(id: &str, c: &domain::swc::SoftwareComponent) -> ComponentResponse {
    ComponentResponse {
        id: id.to_owned(),
        arxml_ref: c.arxml_ref.0.clone(),
        name: c.name.clone(),
        variant: match c.variant {
            domain::swc::AutosarVariant::Classic => AutosarVariant::Classic,
            domain::swc::AutosarVariant::Adaptive => AutosarVariant::Adaptive,
        },
        description: c.description.clone(),
    }
}

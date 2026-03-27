//! REST server — axum router + utoipa OpenAPI spec.

pub mod handlers;
pub mod types;

use axum::{routing, Router};
use utoipa::OpenApi;
use utoipa_swagger_ui::SwaggerUi;

use crate::store::ComponentStore;
use handlers::{delete_component, get_component, list_components, search_components};
use types::{
    AutosarVariant, ComponentResponse, ErrorResponse, ListComponentsQuery,
    ListComponentsResponse, SearchRequest, SearchResponse, SearchResultResponse,
};

/// OpenAPI 3 specification for core-api v1.
#[derive(OpenApi)]
#[openapi(
    info(
        title = "polyarchos core-api",
        version = "0.1.0",
        description = "AUTOSAR Component Intelligence Platform — REST API",
        contact(name = "polyarchos", url = "https://github.com/polyarchos"),
        license(name = "MIT"),
    ),
    paths(
        handlers::get_component,
        handlers::list_components,
        handlers::search_components,
        handlers::delete_component,
    ),
    components(schemas(
        ComponentResponse,
        ListComponentsResponse,
        ListComponentsQuery,
        SearchRequest,
        SearchResponse,
        SearchResultResponse,
        AutosarVariant,
        ErrorResponse,
    )),
    tags(
        (name = "components", description = "AUTOSAR Software Component operations"),
    )
)]
pub struct ApiDoc;

/// Build the axum `Router` with all REST routes and Swagger UI.
pub fn router(store: ComponentStore) -> Router {
    let api_routes = Router::new()
        .route("/components/:id", routing::get(get_component))
        .route("/components/:id", routing::delete(delete_component))
        .route("/components", routing::get(list_components))
        .route("/components/search", routing::post(search_components))
        .with_state(store);

    Router::new()
        .nest("/api/v1", api_routes)
        .merge(
            SwaggerUi::new("/swagger-ui")
                .url("/api-docs/openapi.json", ApiDoc::openapi()),
        )
}

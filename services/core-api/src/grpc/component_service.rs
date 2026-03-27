//! tonic implementation of `ComponentService`.
//!
//! Proto-generated types are mapped to domain types at this boundary.
//! Domain types never leak past this module into business logic.

use tonic::{Request, Response, Status};
use tracing::instrument;

use crate::store::ComponentStore;
use super::proto::{
    component_service_server::ComponentService,
    AutosarVariant as ProtoVariant,
    DeleteComponentRequest, GetComponentRequest, GetComponentResponse,
    ListComponentsRequest, ListComponentsResponse, SearchComponentsRequest,
    SearchComponentsResponse, SearchResult, SoftwareComponent as ProtoComponent,
    ArxmlRef as ProtoArxmlRef,
};

/// tonic service implementation backed by a `ComponentStore`.
#[derive(Clone)]
pub struct GrpcComponentService {
    store: ComponentStore,
}

impl GrpcComponentService {
    /// Create a new service wrapping the given store.
    pub fn new(store: ComponentStore) -> Self {
        Self { store }
    }
}

#[tonic::async_trait]
impl ComponentService for GrpcComponentService {
    /// Retrieve a single component by its server-assigned ID.
    #[instrument(skip(self))]
    async fn get_component(
        &self,
        request: Request<GetComponentRequest>,
    ) -> Result<Response<GetComponentResponse>, Status> {
        let id = &request.into_inner().id;

        let stored = self
            .store
            .get(id)
            .ok_or_else(|| Status::not_found(format!("component '{id}' not found")))?;

        Ok(Response::new(GetComponentResponse {
            component: Some(to_proto(&stored.id, &stored.component)),
        }))
    }

    /// List all components, with optional variant filtering and pagination.
    #[instrument(skip(self))]
    async fn list_components(
        &self,
        request: Request<ListComponentsRequest>,
    ) -> Result<Response<ListComponentsResponse>, Status> {
        let req = request.into_inner();

        let variant_filter = match req.variant_filter {
            v if v == ProtoVariant::Classic as i32 => {
                Some(domain::swc::AutosarVariant::Classic)
            }
            v if v == ProtoVariant::Adaptive as i32 => {
                Some(domain::swc::AutosarVariant::Adaptive)
            }
            _ => None,
        };

        let page_size = if req.page_size <= 0 { 50 } else { req.page_size.min(200) } as usize;

        let mut all = self.store.list(variant_filter);
        let total_count = all.len() as i32;

        // Simple offset-based pagination via opaque token (base10 offset string).
        let offset: usize = req.page_token.parse().unwrap_or(0);
        all.sort_by(|a, b| a.id.cmp(&b.id));
        let page: Vec<_> = all.iter().skip(offset).take(page_size).collect();

        let next_page_token = if offset + page_size < all.len() {
            (offset + page_size).to_string()
        } else {
            String::new()
        };

        Ok(Response::new(ListComponentsResponse {
            components: page.iter().map(|s| to_proto(&s.id, &s.component)).collect(),
            next_page_token,
            total_count,
        }))
    }

    /// Semantic search — stub returning top-k by name prefix match until Phase 4.
    #[instrument(skip(self))]
    async fn search_components(
        &self,
        request: Request<SearchComponentsRequest>,
    ) -> Result<Response<SearchComponentsResponse>, Status> {
        let req = request.into_inner();
        let query = req.query.to_lowercase();
        let top_k = if req.top_k <= 0 { 10 } else { req.top_k.min(50) } as usize;

        // TODO Phase 4: replace with real Milvus vector search.
        let results: Vec<SearchResult> = self
            .store
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
            .map(|s| SearchResult {
                component: Some(to_proto(&s.id, &s.component)),
                score: 1.0, // placeholder until real embeddings land
            })
            .collect();

        Ok(Response::new(SearchComponentsResponse { results }))
    }

    /// Remove a component record.
    #[instrument(skip(self))]
    async fn delete_component(
        &self,
        request: Request<DeleteComponentRequest>,
    ) -> Result<Response<()>, Status> {
        let id = &request.into_inner().id;

        if self.store.delete(id) {
            Ok(Response::new(()))
        } else {
            Err(Status::not_found(format!("component '{id}' not found")))
        }
    }
}

// ── Mapping helpers ───────────────────────────────────────────────────────────

/// Map a domain `SoftwareComponent` to its proto representation.
fn to_proto(id: &str, c: &domain::swc::SoftwareComponent) -> ProtoComponent {
    ProtoComponent {
        id: id.to_owned(),
        arxml_ref: Some(ProtoArxmlRef { path: c.arxml_ref.0.clone() }),
        name: c.name.clone(),
        variant: match c.variant {
            domain::swc::AutosarVariant::Classic => ProtoVariant::Classic as i32,
            domain::swc::AutosarVariant::Adaptive => ProtoVariant::Adaptive as i32,
        },
        description: c.description.clone().unwrap_or_default(),
        ports: vec![],       // TODO Phase 4: load ports from graph
        ingested_at: None,   // TODO Phase 4: record ingestion timestamp
    }
}

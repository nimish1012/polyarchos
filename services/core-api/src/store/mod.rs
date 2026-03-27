//! In-memory component store.
//!
//! Phase 2 uses an in-memory store backed by `Arc<RwLock<HashMap>>`.
//! Phase 4 will replace this with real Neo4j + Milvus backends behind
//! the same `ComponentStore` interface.

use std::{
    collections::HashMap,
    sync::{Arc, RwLock},
};

use domain::swc::{AutosarVariant, SoftwareComponent};
use uuid::Uuid;

/// A component record held in the store, pairing an ID with its data.
#[derive(Debug, Clone)]
pub struct StoredComponent {
    /// Server-assigned UUID.
    pub id: String,
    /// The component data.
    pub component: SoftwareComponent,
}

/// Thread-safe in-memory store for `SoftwareComponent` records.
#[derive(Clone, Default)]
pub struct ComponentStore {
    inner: Arc<RwLock<HashMap<String, SoftwareComponent>>>,
}

impl ComponentStore {
    /// Create an empty store.
    pub fn new() -> Self {
        Self::default()
    }

    /// Insert a component and return its generated ID.
    pub fn insert(&self, component: SoftwareComponent) -> String {
        let id = Uuid::new_v4().to_string();
        self.inner
            .write()
            .expect("store lock poisoned")
            .insert(id.clone(), component);
        id
    }

    /// Retrieve a component by ID.
    pub fn get(&self, id: &str) -> Option<StoredComponent> {
        self.inner
            .read()
            .expect("store lock poisoned")
            .get(id)
            .map(|c| StoredComponent { id: id.to_owned(), component: c.clone() })
    }

    /// List all components, optionally filtered by AUTOSAR variant.
    pub fn list(&self, variant_filter: Option<AutosarVariant>) -> Vec<StoredComponent> {
        self.inner
            .read()
            .expect("store lock poisoned")
            .iter()
            .filter(|(_, c)| {
                variant_filter.as_ref().map_or(true, |v| &c.variant == v)
            })
            .map(|(id, c)| StoredComponent { id: id.clone(), component: c.clone() })
            .collect()
    }

    /// Remove a component. Returns `true` if the record existed.
    pub fn delete(&self, id: &str) -> bool {
        self.inner
            .write()
            .expect("store lock poisoned")
            .remove(id)
            .is_some()
    }

    /// Total number of records in the store.
    pub fn count(&self) -> usize {
        self.inner.read().expect("store lock poisoned").len()
    }
}

// ── Seed helpers (used in tests and local dev) ────────────────────────────────

impl ComponentStore {
    /// Populate the store with synthetic AUTOSAR fixtures for local dev.
    pub fn seed_fixtures(&self) {
        use domain::swc::ArxmlRef;

        let fixtures = vec![
            SoftwareComponent {
                arxml_ref: ArxmlRef("/AUTOSAR/Components/EngineControl".to_owned()),
                name: "EngineControlSWC".to_owned(),
                variant: AutosarVariant::Classic,
                description: Some(
                    "Controls fuel injection and ignition timing via CAN.".to_owned(),
                ),
            },
            SoftwareComponent {
                arxml_ref: ArxmlRef("/AUTOSAR/Components/BrakeControl".to_owned()),
                name: "BrakeControlSWC".to_owned(),
                variant: AutosarVariant::Classic,
                description: Some(
                    "ABS and ESC brake pressure modulation component.".to_owned(),
                ),
            },
            SoftwareComponent {
                arxml_ref: ArxmlRef("/AUTOSAR/Adaptive/PerceptionService".to_owned()),
                name: "PerceptionServiceSWC".to_owned(),
                variant: AutosarVariant::Adaptive,
                description: Some(
                    "ADAS perception pipeline, exposes SOME/IP service interface.".to_owned(),
                ),
            },
        ];

        for f in fixtures {
            self.insert(f);
        }
    }
}

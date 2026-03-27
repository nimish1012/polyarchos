//! AUTOSAR Software Component (SWC) types.

use serde::{Deserialize, Serialize};

/// Distinguishes AUTOSAR Classic and Adaptive software components.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AutosarVariant {
    /// AUTOSAR Classic Platform — static, resource-constrained ECUs.
    Classic,
    /// AUTOSAR Adaptive Platform — POSIX-based, service-oriented (SOME/IP).
    Adaptive,
}

/// A reference to an ARXML element by its fully-qualified short-name path.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ArxmlRef(pub String);

/// An AUTOSAR Software Component descriptor.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SoftwareComponent {
    /// Fully-qualified ARXML short-name path (e.g. `/AUTOSAR/Components/EngineControl`).
    pub arxml_ref: ArxmlRef,
    /// Human-readable name of the component.
    pub name: String,
    /// Whether this is a Classic or Adaptive SWC.
    pub variant: AutosarVariant,
    /// Optional description extracted from the ARXML.
    pub description: Option<String>,
}

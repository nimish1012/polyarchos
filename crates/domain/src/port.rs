//! AUTOSAR Port and Interface types.

use serde::{Deserialize, Serialize};

use crate::swc::ArxmlRef;

/// Direction of a port on a Software Component.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PortDirection {
    /// Provided port — the SWC implements this interface.
    Provided,
    /// Required port — the SWC consumes this interface.
    Required,
}

/// An AUTOSAR Port on a Software Component.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Port {
    /// ARXML reference identifying this port.
    pub arxml_ref: ArxmlRef,
    /// Human-readable port name.
    pub name: String,
    /// Whether this is a provided or required port.
    pub direction: PortDirection,
    /// Reference to the PortInterface this port realises.
    pub interface_ref: ArxmlRef,
}

//! Port connection resolution helpers.
//!
//! Not exported to JS — called by the public `#[wasm_bindgen]` surface in `lib.rs`.

use domain::port::{Port, PortDirection};

/// Returns all (provided, required) pairs whose `interface_ref` values match.
///
/// This represents legal AUTOSAR port connections: a provided port on one SWC can
/// be connected to a required port on another SWC only if both reference the same
/// `PortInterface`.
pub fn find_compatible_pairs(ports: &[Port]) -> Vec<(Port, Port)> {
    let mut pairs = Vec::new();
    for i in 0..ports.len() {
        for j in (i + 1)..ports.len() {
            let a = &ports[i];
            let b = &ports[j];
            if a.interface_ref == b.interface_ref {
                match (&a.direction, &b.direction) {
                    (PortDirection::Provided, PortDirection::Required) => {
                        pairs.push((a.clone(), b.clone()));
                    }
                    (PortDirection::Required, PortDirection::Provided) => {
                        // Normalise: provided is always first in the pair.
                        pairs.push((b.clone(), a.clone()));
                    }
                    _ => {}
                }
            }
        }
    }
    pairs
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use domain::swc::ArxmlRef;

    fn make_port(name: &str, direction: PortDirection, iface: &str) -> Port {
        Port {
            arxml_ref: ArxmlRef(format!("/Components/Engine/{name}")),
            name: name.to_owned(),
            direction,
            interface_ref: ArxmlRef(iface.to_owned()),
        }
    }

    #[test]
    fn finds_matching_provided_required_pair() {
        let ports = vec![
            make_port("FuelOut", PortDirection::Provided, "/Interfaces/Fuel"),
            make_port("FuelIn", PortDirection::Required, "/Interfaces/Fuel"),
        ];
        let pairs = find_compatible_pairs(&ports);
        assert_eq!(pairs.len(), 1);
        assert_eq!(pairs[0].0.name, "FuelOut"); // provided first
        assert_eq!(pairs[0].1.name, "FuelIn");
    }

    #[test]
    fn ignores_same_direction_same_interface() {
        let ports = vec![
            make_port("PortA", PortDirection::Provided, "/Interfaces/Fuel"),
            make_port("PortB", PortDirection::Provided, "/Interfaces/Fuel"),
        ];
        assert!(find_compatible_pairs(&ports).is_empty());
    }

    #[test]
    fn ignores_mismatched_interface() {
        let ports = vec![
            make_port("PortA", PortDirection::Provided, "/Interfaces/Fuel"),
            make_port("PortB", PortDirection::Required, "/Interfaces/Sensor"),
        ];
        assert!(find_compatible_pairs(&ports).is_empty());
    }

    #[test]
    fn normalises_required_provided_order() {
        let ports = vec![
            make_port("FuelIn", PortDirection::Required, "/Interfaces/Fuel"),
            make_port("FuelOut", PortDirection::Provided, "/Interfaces/Fuel"),
        ];
        let pairs = find_compatible_pairs(&ports);
        assert_eq!(pairs.len(), 1);
        assert_eq!(pairs[0].0.direction, PortDirection::Provided);
    }
}

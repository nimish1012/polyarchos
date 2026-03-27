//! polyarchos WASM bindings.
//!
//! Exports AUTOSAR domain logic for use in browser environments via wasm-bindgen.
//! All exported functions are panic-free — errors are surfaced as JS exceptions
//! (`JsError`) so callers can use standard `try/catch`.
//!
//! # Quick start (TypeScript)
//!
//! ```ts
//! import init, {
//!   version,
//!   parse_arxml_component,
//!   validate_component,
//!   classify_variant,
//!   resolve_port_connections,
//! } from "./pkg/polyarchos_wasm.js";
//!
//! await init();
//! console.log(version()); // "0.1.0"
//! ```

#![deny(clippy::all)]
#![deny(missing_docs)]

mod arxml;
mod ports;

use serde::Serialize;
use wasm_bindgen::prelude::*;

// ── Module init ───────────────────────────────────────────────────────────────

/// Initialises the WASM module.
///
/// Call once after `await init()`. Installs a panic hook that routes Rust panics
/// to `console.error` in the browser, producing readable stack traces instead of
/// opaque `RuntimeError: unreachable` messages.
#[wasm_bindgen(start)]
pub fn module_init() {
    console_error_panic_hook::set_once();
}

// ── Utilities ─────────────────────────────────────────────────────────────────

/// Returns the crate version string (matches `Cargo.toml` `version`).
///
/// Used by the frontend to verify the WASM module loaded correctly.
#[wasm_bindgen]
pub fn version() -> String {
    env!("CARGO_PKG_VERSION").to_owned()
}

/// Classifies an ARXML short-name path as `"classic"` or `"adaptive"`.
///
/// Heuristic: paths containing the segment `/Adaptive/` (case-sensitive) are
/// classified as Adaptive; all other paths default to Classic.
///
/// # Example
///
/// ```ts
/// classify_variant("/AUTOSAR/Adaptive/PerceptionService"); // → '"adaptive"'
/// classify_variant("/AUTOSAR/Components/EngineControl");   // → '"classic"'
/// ```
#[wasm_bindgen]
pub fn classify_variant(arxml_path: &str) -> String {
    use domain::swc::AutosarVariant;
    let v = if arxml_path.contains("/Adaptive/") {
        AutosarVariant::Adaptive
    } else {
        AutosarVariant::Classic
    };
    // Returns JSON string: `"classic"` or `"adaptive"` (matches serde rename_all = "snake_case").
    serde_json::to_string(&v).unwrap_or_else(|_| r#""classic""#.to_owned())
}

// ── ARXML parsing ─────────────────────────────────────────────────────────────

/// Shape returned by [`parse_arxml_component`].
#[derive(Serialize)]
struct ParsedArxmlResult {
    component: domain::swc::SoftwareComponent,
    ports: Vec<domain::port::Port>,
}

/// Parses an ARXML XML string and extracts the first SWC definition found.
///
/// Supports:
/// - `APPLICATION-SW-COMPONENT-TYPE` → Classic
/// - `ADAPTIVE-APPLICATION-SW-COMPONENT-TYPE` → Adaptive
/// - `SENSOR-ACTUATOR-SW-COMPONENT-TYPE`, `COMPLEX-DEVICE-DRIVER-SW-COMPONENT-TYPE`,
///   `ECU-ABSTRACTION-SW-COMPONENT-TYPE`, `SERVICE-SW-COMPONENT-TYPE` → Classic
///
/// Returns a JSON object `{ component: SoftwareComponent, ports: Port[] }`.
///
/// # Errors
///
/// Throws a descriptive error string if the XML is malformed or no SWC element
/// is found in the document.
#[wasm_bindgen]
pub fn parse_arxml_component(xml: &str) -> Result<JsValue, JsError> {
    let doc = roxmltree::Document::parse(xml)
        .map_err(|e| JsError::new(&format!("XML parse error: {e}")))?;

    let (swc_node, variant) = arxml::find_swc_node(&doc).ok_or_else(|| {
        JsError::new(
            "No SWC element found — expected APPLICATION-SW-COMPONENT-TYPE \
             or ADAPTIVE-APPLICATION-SW-COMPONENT-TYPE",
        )
    })?;

    let name = swc_node
        .children()
        .find(|n| n.tag_name().name() == "SHORT-NAME")
        .and_then(|n| n.text())
        .ok_or_else(|| JsError::new("SWC element is missing SHORT-NAME child"))?
        .to_owned();

    let description = swc_node
        .children()
        .find(|n| n.tag_name().name() == "LONG-NAME")
        .and_then(|n| n.text())
        .map(ToOwned::to_owned);

    let arxml_path = arxml::build_arxml_path(&swc_node, &name);
    let port_list = arxml::parse_ports(&swc_node, &arxml_path);

    let result = ParsedArxmlResult {
        component: domain::swc::SoftwareComponent {
            arxml_ref: domain::swc::ArxmlRef(arxml_path),
            name,
            variant,
            description,
        },
        ports: port_list,
    };

    let json = serde_json::to_string(&result)
        .map_err(|e| JsError::new(&format!("Serialisation error: {e}")))?;
    Ok(JsValue::from_str(&json))
}

// ── Validation ────────────────────────────────────────────────────────────────

/// Validates a JSON-encoded `SoftwareComponent`.
///
/// Checks:
/// - `name` is non-empty (after trimming whitespace)
/// - `arxml_ref` is an absolute AUTOSAR short-name path (starts with `/`)
/// - `arxml_ref` contains no consecutive slashes (`//`)
///
/// # Errors
///
/// Throws a semicolon-separated error string if any check fails.
#[wasm_bindgen]
pub fn validate_component(json: &str) -> Result<(), JsError> {
    let component: domain::swc::SoftwareComponent = serde_json::from_str(json)
        .map_err(|e| JsError::new(&format!("JSON parse error: {e}")))?;

    let errors = arxml::validate_swc(&component);
    if errors.is_empty() {
        Ok(())
    } else {
        Err(JsError::new(&errors.join("; ")))
    }
}

// ── Port resolution ───────────────────────────────────────────────────────────

/// Resolves compatible port connection pairs from a JSON array of `Port` objects.
///
/// Two ports are compatible when they share the same `interface_ref` and have
/// opposite directions (`provided` ↔ `required`). This mirrors the AUTOSAR rule
/// that an `R-PORT-PROTOTYPE` may only connect to a `P-PORT-PROTOTYPE` realising
/// the same `PortInterface`.
///
/// Returns a JSON array of `[providedPort, requiredPort]` tuples.
///
/// # Errors
///
/// Throws a descriptive error string if the input JSON cannot be deserialised.
#[wasm_bindgen]
pub fn resolve_port_connections(ports_json: &str) -> Result<JsValue, JsError> {
    let port_list: Vec<domain::port::Port> = serde_json::from_str(ports_json)
        .map_err(|e| JsError::new(&format!("JSON parse error: {e}")))?;

    let pairs = ports::find_compatible_pairs(&port_list);

    let json = serde_json::to_string(&pairs)
        .map_err(|e| JsError::new(&format!("Serialisation error: {e}")))?;
    Ok(JsValue::from_str(&json))
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    #[test]
    fn version_is_nonempty() {
        assert!(!super::version().is_empty());
    }

    #[test]
    fn classify_variant_adaptive() {
        assert_eq!(
            super::classify_variant("/AUTOSAR/Adaptive/PerceptionService"),
            r#""adaptive""#
        );
    }

    #[test]
    fn classify_variant_classic() {
        assert_eq!(
            super::classify_variant("/AUTOSAR/Components/EngineControl"),
            r#""classic""#
        );
    }
}

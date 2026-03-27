//! Internal ARXML parsing and validation helpers.
//!
//! Not exported to JS — called by the public `#[wasm_bindgen]` surface in `lib.rs`.

use domain::{
    port::{Port, PortDirection},
    swc::{ArxmlRef, AutosarVariant, SoftwareComponent},
};
use roxmltree::{Document, Node};

/// Maps an ARXML element tag to its AUTOSAR variant.
///
/// Returns `None` for tags that are not SWC component elements.
pub fn variant_from_tag(tag: &str) -> Option<AutosarVariant> {
    match tag {
        "APPLICATION-SW-COMPONENT-TYPE"
        | "SENSOR-ACTUATOR-SW-COMPONENT-TYPE"
        | "COMPLEX-DEVICE-DRIVER-SW-COMPONENT-TYPE"
        | "ECU-ABSTRACTION-SW-COMPONENT-TYPE"
        | "SERVICE-SW-COMPONENT-TYPE" => Some(AutosarVariant::Classic),
        "ADAPTIVE-APPLICATION-SW-COMPONENT-TYPE" => Some(AutosarVariant::Adaptive),
        _ => None,
    }
}

/// Finds the first SWC element in the document and returns it with its detected variant.
pub fn find_swc_node<'a, 'input>(
    doc: &'a Document<'input>,
) -> Option<(Node<'a, 'input>, AutosarVariant)> {
    doc.descendants()
        .find_map(|n| variant_from_tag(n.tag_name().name()).map(|v| (n, v)))
}

/// Builds an ARXML absolute short-name path for a SWC by walking up `AR-PACKAGE` ancestors.
///
/// For a document structured as `/AUTOSAR/Components/EngineControlSWC`, this returns
/// exactly that path string.
pub fn build_arxml_path(node: &Node<'_, '_>, swc_name: &str) -> String {
    let mut parts: Vec<String> = Vec::new();
    let mut cur = node.parent();
    while let Some(n) = cur {
        if n.tag_name().name() == "AR-PACKAGE" {
            if let Some(sn) = n
                .children()
                .find(|c| c.tag_name().name() == "SHORT-NAME")
                .and_then(|c| c.text())
            {
                parts.push(sn.to_owned());
            }
        }
        cur = n.parent();
    }
    parts.reverse();
    if parts.is_empty() {
        format!("/{swc_name}")
    } else {
        format!("/{}/{swc_name}", parts.join("/"))
    }
}

/// Extracts all `P-PORT-PROTOTYPE` and `R-PORT-PROTOTYPE` children from a SWC node.
pub fn parse_ports(swc_node: &Node<'_, '_>, swc_path: &str) -> Vec<Port> {
    let Some(ports_node) = swc_node
        .children()
        .find(|n| n.tag_name().name() == "PORTS")
    else {
        return Vec::new();
    };

    ports_node
        .children()
        .filter(|n| n.is_element())
        .filter_map(|n| {
            let direction = match n.tag_name().name() {
                "P-PORT-PROTOTYPE" => PortDirection::Provided,
                "R-PORT-PROTOTYPE" => PortDirection::Required,
                _ => return None,
            };
            let name = n
                .children()
                .find(|c| c.tag_name().name() == "SHORT-NAME")
                .and_then(|c| c.text())
                .unwrap_or("unknown")
                .to_owned();
            // ARXML uses different TREF element names per interface type, but all end in
            // "-INTERFACE-TREF" (e.g. PROVIDED-INTERFACE-TREF, REQUIRED-INTERFACE-TREF).
            let iface_ref = n
                .children()
                .find(|c| c.tag_name().name().ends_with("-INTERFACE-TREF"))
                .and_then(|c| c.text())
                .unwrap_or("/Unknown/Interface")
                .to_owned();
            Some(Port {
                arxml_ref: ArxmlRef(format!("{swc_path}/{name}")),
                name,
                direction,
                interface_ref: ArxmlRef(iface_ref),
            })
        })
        .collect()
}

/// Returns a list of human-readable validation errors for a `SoftwareComponent`.
///
/// An empty vec means the component is valid.
pub fn validate_swc(c: &SoftwareComponent) -> Vec<String> {
    let mut errors = Vec::new();
    if c.name.trim().is_empty() {
        errors.push("name must not be empty".to_owned());
    }
    if !c.arxml_ref.0.starts_with('/') {
        errors.push(format!(
            "arxml_ref '{}' must be an absolute path starting with '/'",
            c.arxml_ref.0
        ));
    }
    if c.arxml_ref.0.contains("//") {
        errors.push(format!(
            "arxml_ref '{}' contains consecutive slashes",
            c.arxml_ref.0
        ));
    }
    errors
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use domain::swc::{ArxmlRef, SoftwareComponent};

    #[test]
    fn variant_from_tag_classic() {
        assert_eq!(
            variant_from_tag("APPLICATION-SW-COMPONENT-TYPE"),
            Some(AutosarVariant::Classic)
        );
        assert_eq!(
            variant_from_tag("SENSOR-ACTUATOR-SW-COMPONENT-TYPE"),
            Some(AutosarVariant::Classic)
        );
    }

    #[test]
    fn variant_from_tag_adaptive() {
        assert_eq!(
            variant_from_tag("ADAPTIVE-APPLICATION-SW-COMPONENT-TYPE"),
            Some(AutosarVariant::Adaptive)
        );
    }

    #[test]
    fn variant_from_tag_unknown() {
        assert_eq!(variant_from_tag("AR-PACKAGE"), None);
    }

    #[test]
    fn validate_swc_valid() {
        let swc = SoftwareComponent {
            arxml_ref: ArxmlRef("/AUTOSAR/Components/Engine".to_owned()),
            name: "EngineControl".to_owned(),
            variant: AutosarVariant::Classic,
            description: None,
        };
        assert!(validate_swc(&swc).is_empty());
    }

    #[test]
    fn validate_swc_empty_name() {
        let swc = SoftwareComponent {
            arxml_ref: ArxmlRef("/AUTOSAR/Components/Engine".to_owned()),
            name: "  ".to_owned(),
            variant: AutosarVariant::Classic,
            description: None,
        };
        let errors = validate_swc(&swc);
        assert!(errors.iter().any(|e| e.contains("name")));
    }

    #[test]
    fn validate_swc_relative_path() {
        let swc = SoftwareComponent {
            arxml_ref: ArxmlRef("AUTOSAR/Components/Engine".to_owned()),
            name: "EngineControl".to_owned(),
            variant: AutosarVariant::Classic,
            description: None,
        };
        let errors = validate_swc(&swc);
        assert!(errors.iter().any(|e| e.contains("absolute")));
    }

    #[test]
    fn find_swc_parses_classic() {
        let xml = r#"<AUTOSAR>
  <AR-PACKAGES><AR-PACKAGE>
    <SHORT-NAME>Components</SHORT-NAME>
    <ELEMENTS>
      <APPLICATION-SW-COMPONENT-TYPE>
        <SHORT-NAME>EngineControlSWC</SHORT-NAME>
      </APPLICATION-SW-COMPONENT-TYPE>
    </ELEMENTS>
  </AR-PACKAGE></AR-PACKAGES>
</AUTOSAR>"#;
        let doc = Document::parse(xml).unwrap();
        let (_, variant) = find_swc_node(&doc).unwrap();
        assert_eq!(variant, AutosarVariant::Classic);
    }

    #[test]
    fn build_arxml_path_nested_packages() {
        let xml = r#"<AUTOSAR>
  <AR-PACKAGES><AR-PACKAGE>
    <SHORT-NAME>AUTOSAR</SHORT-NAME>
    <AR-PACKAGES><AR-PACKAGE>
      <SHORT-NAME>Components</SHORT-NAME>
      <ELEMENTS>
        <APPLICATION-SW-COMPONENT-TYPE>
          <SHORT-NAME>EngineControlSWC</SHORT-NAME>
        </APPLICATION-SW-COMPONENT-TYPE>
      </ELEMENTS>
    </AR-PACKAGE></AR-PACKAGES>
  </AR-PACKAGE></AR-PACKAGES>
</AUTOSAR>"#;
        let doc = Document::parse(xml).unwrap();
        let (node, _) = find_swc_node(&doc).unwrap();
        let path = build_arxml_path(&node, "EngineControlSWC");
        assert_eq!(path, "/AUTOSAR/Components/EngineControlSWC");
    }

    #[test]
    fn parse_ports_extracts_provided_and_required() {
        let xml = r#"<AUTOSAR><AR-PACKAGES><AR-PACKAGE>
  <SHORT-NAME>Components</SHORT-NAME><ELEMENTS>
  <APPLICATION-SW-COMPONENT-TYPE>
    <SHORT-NAME>Engine</SHORT-NAME>
    <PORTS>
      <P-PORT-PROTOTYPE>
        <SHORT-NAME>FuelPort</SHORT-NAME>
        <PROVIDED-INTERFACE-TREF>/Interfaces/Fuel</PROVIDED-INTERFACE-TREF>
      </P-PORT-PROTOTYPE>
      <R-PORT-PROTOTYPE>
        <SHORT-NAME>SensorPort</SHORT-NAME>
        <REQUIRED-INTERFACE-TREF>/Interfaces/Sensor</REQUIRED-INTERFACE-TREF>
      </R-PORT-PROTOTYPE>
    </PORTS>
  </APPLICATION-SW-COMPONENT-TYPE>
  </ELEMENTS></AR-PACKAGE></AR-PACKAGES></AUTOSAR>"#;
        let doc = Document::parse(xml).unwrap();
        let (node, _) = find_swc_node(&doc).unwrap();
        let ports = parse_ports(&node, "/Components/Engine");
        assert_eq!(ports.len(), 2);
        assert_eq!(ports[0].direction, PortDirection::Provided);
        assert_eq!(ports[0].name, "FuelPort");
        assert_eq!(ports[1].direction, PortDirection::Required);
        assert_eq!(ports[1].name, "SensorPort");
    }
}

"""AUTOSAR ARXML parser — extracts SWC definitions from ARXML XML documents.

Uses the stdlib ``xml.etree.ElementTree`` for schema-aware XML parsing.
Supports both AUTOSAR Classic and Adaptive SWC element types.
Handles the AUTOSAR 4.x namespace (``http://autosar.org/schema/conf/4.0``)
transparently by stripping namespace prefixes before tag comparison.

No string-matching on raw XML text is performed anywhere in this module.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class AutosarVariant(str, Enum):
    """AUTOSAR platform variant."""

    CLASSIC = "classic"
    ADAPTIVE = "adaptive"


class PortDirection(str, Enum):
    """Direction of an AUTOSAR port prototype."""

    PROVIDED = "provided"
    REQUIRED = "required"


@dataclass
class PortRecord:
    """A parsed P-PORT-PROTOTYPE or R-PORT-PROTOTYPE."""

    name: str
    arxml_ref: str
    direction: PortDirection
    interface_ref: str


@dataclass
class SoftwareComponentRecord:
    """A parsed APPLICATION-SW-COMPONENT-TYPE or ADAPTIVE-APPLICATION-SW-COMPONENT-TYPE."""

    name: str
    arxml_ref: str
    variant: AutosarVariant
    description: str
    ports: list[PortRecord] = field(default_factory=list)

    def to_text_chunk(self) -> str:
        """Build a human-readable text chunk suitable for embedding and RAG retrieval."""
        lines = [
            f"AUTOSAR {self.variant.value.title()} SWC: {self.name}",
            f"ARXML path: {self.arxml_ref}",
        ]
        if self.description:
            lines.append(f"Description: {self.description}")
        if self.ports:
            lines.append("Ports:")
            for port in self.ports:
                lines.append(
                    f"  - {port.name} ({port.direction.value})"
                    f" → interface: {port.interface_ref}"
                )
        return "\n".join(lines)


@dataclass
class ArxmlDocument:
    """The result of parsing an ARXML file."""

    document_name: str
    components: list[SoftwareComponentRecord] = field(default_factory=list)


# ── AUTOSAR element tag sets ──────────────────────────────────────────────────

_CLASSIC_SWC_TAGS: frozenset[str] = frozenset(
    {
        "APPLICATION-SW-COMPONENT-TYPE",
        "SENSOR-ACTUATOR-SW-COMPONENT-TYPE",
        "COMPLEX-DEVICE-DRIVER-SW-COMPONENT-TYPE",
        "ECU-ABSTRACTION-SW-COMPONENT-TYPE",
        "SERVICE-SW-COMPONENT-TYPE",
    }
)

_ADAPTIVE_SWC_TAGS: frozenset[str] = frozenset(
    {"ADAPTIVE-APPLICATION-SW-COMPONENT-TYPE"}
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _strip_ns(tag: str) -> str:
    """Strip XML namespace prefix, e.g. ``{http://...}SHORT-NAME`` → ``SHORT-NAME``."""
    return tag.split("}")[-1] if "}" in tag else tag


def _child_text(element: ET.Element, tag: str) -> str:
    """Return trimmed text of the first direct child whose (ns-stripped) tag matches."""
    for child in element:
        if _strip_ns(child.tag) == tag:
            return (child.text or "").strip()
    return ""


def _build_arxml_path(ancestors: list[ET.Element], swc_name: str) -> str:
    """Collect SHORT-NAMEs from AR-PACKAGE ancestors to form an absolute path."""
    parts: list[str] = []
    for ancestor in ancestors:
        if _strip_ns(ancestor.tag) == "AR-PACKAGE":
            sn = _child_text(ancestor, "SHORT-NAME")
            if sn:
                parts.append(sn)
    if parts:
        return "/" + "/".join(parts) + "/" + swc_name
    return "/" + swc_name


def _parse_ports(swc_element: ET.Element, swc_path: str) -> list[PortRecord]:
    """Extract all P-PORT-PROTOTYPE and R-PORT-PROTOTYPE children."""
    ports_el = next(
        (c for c in swc_element if _strip_ns(c.tag) == "PORTS"),
        None,
    )
    if ports_el is None:
        return []

    records: list[PortRecord] = []
    for port_el in ports_el:
        tag = _strip_ns(port_el.tag)
        if tag == "P-PORT-PROTOTYPE":
            direction = PortDirection.PROVIDED
        elif tag == "R-PORT-PROTOTYPE":
            direction = PortDirection.REQUIRED
        else:
            continue

        port_name = _child_text(port_el, "SHORT-NAME")
        # Interface tref element name varies by interface type but always ends in
        # "-INTERFACE-TREF" (e.g. PROVIDED-INTERFACE-TREF, REQUIRED-INTERFACE-TREF).
        iface_ref = next(
            (
                (c.text or "").strip()
                for c in port_el
                if _strip_ns(c.tag).endswith("-INTERFACE-TREF")
            ),
            "/Unknown/Interface",
        )
        records.append(
            PortRecord(
                name=port_name,
                arxml_ref=f"{swc_path}/{port_name}",
                direction=direction,
                interface_ref=iface_ref,
            )
        )
    return records


def _walk(
    element: ET.Element,
    ancestors: list[ET.Element],
    out: list[SoftwareComponentRecord],
) -> None:
    """Recursively walk the element tree, collecting SWC records."""
    tag = _strip_ns(element.tag)

    if tag in _CLASSIC_SWC_TAGS:
        variant = AutosarVariant.CLASSIC
    elif tag in _ADAPTIVE_SWC_TAGS:
        variant = AutosarVariant.ADAPTIVE
    else:
        # Not a SWC element — recurse into children.
        for child in element:
            _walk(child, [*ancestors, element], out)
        return

    name = _child_text(element, "SHORT-NAME")
    description = _child_text(element, "LONG-NAME")
    arxml_path = _build_arxml_path(ancestors, name)
    ports = _parse_ports(element, arxml_path)

    out.append(
        SoftwareComponentRecord(
            name=name,
            arxml_ref=arxml_path,
            variant=variant,
            description=description,
            ports=ports,
        )
    )


# ── Public API ────────────────────────────────────────────────────────────────


def parse_arxml(content: str | bytes, document_name: str) -> ArxmlDocument:
    """Parse an ARXML document and extract all SWC definitions.

    Args:
        content: Raw ARXML XML as a string or UTF-8 bytes.
        document_name: Logical name used as the ingestion idempotency key.

    Returns:
        :class:`ArxmlDocument` containing all discovered
        :class:`SoftwareComponentRecord` instances.

    Raises:
        xml.etree.ElementTree.ParseError: If the XML is malformed.
    """
    if isinstance(content, bytes):
        content = content.decode("utf-8")

    root = ET.fromstring(content)
    components: list[SoftwareComponentRecord] = []
    _walk(root, [], components)
    return ArxmlDocument(document_name=document_name, components=components)


def parse_arxml_file(path: Path, document_name: str | None = None) -> ArxmlDocument:
    """Convenience wrapper — parse an ARXML file from disk."""
    return parse_arxml(path.read_text(encoding="utf-8"), document_name or path.name)

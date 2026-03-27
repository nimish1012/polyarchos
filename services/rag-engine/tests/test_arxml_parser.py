"""Tests for rag_engine.arxml_parser — mirrors source at src/rag_engine/arxml_parser.py."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from rag_engine.arxml_parser import (
    AutosarVariant,
    PortDirection,
    parse_arxml,
    parse_arxml_file,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "tests" / "fixtures"


def _minimal_arxml(swc_tag: str, swc_name: str, extra: str = "") -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<AUTOSAR>
  <AR-PACKAGES>
    <AR-PACKAGE>
      <SHORT-NAME>TestPkg</SHORT-NAME>
      <ELEMENTS>
        <{swc_tag}>
          <SHORT-NAME>{swc_name}</SHORT-NAME>
          {extra}
        </{swc_tag}>
      </ELEMENTS>
    </AR-PACKAGE>
  </AR-PACKAGES>
</AUTOSAR>"""


# ── Basic parsing ─────────────────────────────────────────────────────────────


def test_parse_classic_swc() -> None:
    xml = _minimal_arxml("APPLICATION-SW-COMPONENT-TYPE", "EngineControl")
    doc = parse_arxml(xml, "test")
    assert len(doc.components) == 1
    comp = doc.components[0]
    assert comp.name == "EngineControl"
    assert comp.variant == AutosarVariant.CLASSIC
    assert comp.arxml_ref == "/TestPkg/EngineControl"


def test_parse_adaptive_swc() -> None:
    xml = _minimal_arxml("ADAPTIVE-APPLICATION-SW-COMPONENT-TYPE", "PerceptionSvc")
    doc = parse_arxml(xml, "test")
    assert len(doc.components) == 1
    assert doc.components[0].variant == AutosarVariant.ADAPTIVE


def test_parse_sensor_actuator_swc() -> None:
    xml = _minimal_arxml("SENSOR-ACTUATOR-SW-COMPONENT-TYPE", "WheelSpeedSensor")
    doc = parse_arxml(xml, "test")
    assert len(doc.components) == 1
    assert doc.components[0].variant == AutosarVariant.CLASSIC


def test_parse_bytes_input() -> None:
    xml = _minimal_arxml("APPLICATION-SW-COMPONENT-TYPE", "MyComp")
    doc = parse_arxml(xml.encode("utf-8"), "test")
    assert len(doc.components) == 1


def test_empty_document_returns_no_components() -> None:
    xml = "<AUTOSAR><AR-PACKAGES/></AUTOSAR>"
    doc = parse_arxml(xml, "empty")
    assert doc.components == []


def test_malformed_xml_raises() -> None:
    with pytest.raises(ET.ParseError):
        parse_arxml("<not valid xml", "bad")


# ── ARXML path building ───────────────────────────────────────────────────────


def test_nested_package_path() -> None:
    xml = """<AUTOSAR>
  <AR-PACKAGES><AR-PACKAGE>
    <SHORT-NAME>Root</SHORT-NAME>
    <AR-PACKAGES><AR-PACKAGE>
      <SHORT-NAME>Sub</SHORT-NAME>
      <ELEMENTS>
        <APPLICATION-SW-COMPONENT-TYPE>
          <SHORT-NAME>Comp</SHORT-NAME>
        </APPLICATION-SW-COMPONENT-TYPE>
      </ELEMENTS>
    </AR-PACKAGE></AR-PACKAGES>
  </AR-PACKAGE></AR-PACKAGES>
</AUTOSAR>"""
    doc = parse_arxml(xml, "test")
    assert doc.components[0].arxml_ref == "/Root/Sub/Comp"


# ── Port parsing ──────────────────────────────────────────────────────────────


def test_parse_provided_and_required_ports() -> None:
    port_xml = """
    <PORTS>
      <P-PORT-PROTOTYPE>
        <SHORT-NAME>FuelOut</SHORT-NAME>
        <PROVIDED-INTERFACE-TREF>/Ifaces/FuelIf</PROVIDED-INTERFACE-TREF>
      </P-PORT-PROTOTYPE>
      <R-PORT-PROTOTYPE>
        <SHORT-NAME>SpeedIn</SHORT-NAME>
        <REQUIRED-INTERFACE-TREF>/Ifaces/SpeedIf</REQUIRED-INTERFACE-TREF>
      </R-PORT-PROTOTYPE>
    </PORTS>"""
    xml = _minimal_arxml("APPLICATION-SW-COMPONENT-TYPE", "Engine", port_xml)
    doc = parse_arxml(xml, "test")
    comp = doc.components[0]
    assert len(comp.ports) == 2

    provided = next(p for p in comp.ports if p.direction == PortDirection.PROVIDED)
    assert provided.name == "FuelOut"
    assert provided.interface_ref == "/Ifaces/FuelIf"
    assert provided.arxml_ref == "/TestPkg/Engine/FuelOut"

    required = next(p for p in comp.ports if p.direction == PortDirection.REQUIRED)
    assert required.name == "SpeedIn"
    assert required.interface_ref == "/Ifaces/SpeedIf"


def test_swc_without_ports() -> None:
    xml = _minimal_arxml("APPLICATION-SW-COMPONENT-TYPE", "NoPorts")
    doc = parse_arxml(xml, "test")
    assert doc.components[0].ports == []


# ── Text chunk ────────────────────────────────────────────────────────────────


def test_to_text_chunk_includes_name_and_variant() -> None:
    xml = _minimal_arxml("APPLICATION-SW-COMPONENT-TYPE", "EngineControl")
    comp = parse_arxml(xml, "test").components[0]
    chunk = comp.to_text_chunk()
    assert "EngineControl" in chunk
    assert "Classic" in chunk


def test_to_text_chunk_lists_ports() -> None:
    port_xml = """
    <PORTS>
      <P-PORT-PROTOTYPE>
        <SHORT-NAME>FuelOut</SHORT-NAME>
        <PROVIDED-INTERFACE-TREF>/Ifaces/Fuel</PROVIDED-INTERFACE-TREF>
      </P-PORT-PROTOTYPE>
    </PORTS>"""
    xml = _minimal_arxml("APPLICATION-SW-COMPONENT-TYPE", "Engine", port_xml)
    comp = parse_arxml(xml, "test").components[0]
    chunk = comp.to_text_chunk()
    assert "FuelOut" in chunk
    assert "provided" in chunk


# ── Sample fixture ────────────────────────────────────────────────────────────


def test_sample_arxml_fixture() -> None:
    """Smoke-test the synthetic ARXML fixture — ensures it parses cleanly."""
    fixture = FIXTURES_DIR / "sample.arxml"
    doc = parse_arxml_file(fixture, "sample")

    assert len(doc.components) == 4  # 3 Classic + 1 Adaptive

    names = {c.name for c in doc.components}
    assert "EngineControlSWC" in names
    assert "BrakeControlSWC" in names
    assert "WheelSpeedSensorSWC" in names
    assert "PerceptionServiceSWC" in names

    classic = [c for c in doc.components if c.variant == AutosarVariant.CLASSIC]
    adaptive = [c for c in doc.components if c.variant == AutosarVariant.ADAPTIVE]
    assert len(classic) == 3
    assert len(adaptive) == 1


def test_sample_arxml_ports() -> None:
    fixture = FIXTURES_DIR / "sample.arxml"
    doc = parse_arxml_file(fixture, "sample")

    engine = next(c for c in doc.components if c.name == "EngineControlSWC")
    assert len(engine.ports) == 2

    provided = next(p for p in engine.ports if p.direction == PortDirection.PROVIDED)
    assert "FuelInjection" in provided.interface_ref

    required = next(p for p in engine.ports if p.direction == PortDirection.REQUIRED)
    assert "EngineSpeed" in required.interface_ref


def test_sample_arxml_namespace_stripped() -> None:
    """Verify namespace-prefixed ARXML also parses correctly."""
    ns_xml = """<?xml version="1.0" encoding="UTF-8"?>
<AUTOSAR xmlns="http://autosar.org/schema/conf/4.0">
  <AR-PACKAGES><AR-PACKAGE>
    <SHORT-NAME>NS</SHORT-NAME>
    <ELEMENTS>
      <APPLICATION-SW-COMPONENT-TYPE>
        <SHORT-NAME>NsComp</SHORT-NAME>
      </APPLICATION-SW-COMPONENT-TYPE>
    </ELEMENTS>
  </AR-PACKAGE></AR-PACKAGES>
</AUTOSAR>"""
    doc = parse_arxml(ns_xml, "ns-test")
    assert len(doc.components) == 1
    assert doc.components[0].name == "NsComp"

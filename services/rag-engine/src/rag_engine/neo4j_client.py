"""Neo4j graph client for AUTOSAR component relationships.

Graph schema
------------
Nodes:
  (:SoftwareComponent {arxml_ref, name, variant, description})
  (:Port              {arxml_ref, name, direction})
  (:Interface         {arxml_ref})

Relationships:
  (:SoftwareComponent)-[:HAS_PORT]->(:Port)
  (:Port)-[:REALIZES]->(:Interface)           # provided ports
  (:Port)-[:REQUIRES_INTERFACE]->(:Interface) # required ports

All node merges are idempotent via the ``arxml_ref`` uniqueness constraint.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from neo4j import AsyncDriver, AsyncGraphDatabase  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


@dataclass
class PortData:
    """Port data used for graph node creation."""

    name: str
    arxml_ref: str
    direction: str  # "provided" | "required"
    interface_ref: str


@dataclass
class ComponentData:
    """SWC data used for graph node creation."""

    name: str
    arxml_ref: str
    variant: str
    description: str
    ports: list[PortData] = field(default_factory=list)


class Neo4jComponentGraph:
    """Async Neo4j client that manages the AUTOSAR component graph."""

    def __init__(self, uri: str, user: str, password: str) -> None:
        self._uri = uri
        self._user = user
        self._password = password
        self._driver: AsyncDriver | None = None

    async def connect(self) -> None:
        """Open the driver and ensure schema constraints exist."""
        self._driver = AsyncGraphDatabase.driver(
            self._uri, auth=(self._user, self._password)
        )
        await self._ensure_constraints()
        logger.info("Connected to Neo4j", extra={"uri": self._uri})

    async def close(self) -> None:
        """Close the driver and release connection resources."""
        if self._driver:
            await self._driver.close()

    async def _ensure_constraints(self) -> None:
        """Create uniqueness constraints if they don't already exist."""
        if self._driver is None:
            return
        async with self._driver.session() as session:
            for label in ("SoftwareComponent", "Port", "Interface"):
                await session.run(
                    f"CREATE CONSTRAINT IF NOT EXISTS "
                    f"FOR (n:{label}) REQUIRE n.arxml_ref IS UNIQUE"
                )

    async def upsert_component(self, data: ComponentData) -> int:
        """Merge a SWC node and all its ports/interfaces into the graph.

        Uses Cypher ``MERGE`` throughout, making the operation idempotent.

        Returns:
            Total number of graph edges created or matched.
        """
        if self._driver is None:
            return 0

        edges = 0
        async with self._driver.session() as session:
            # Upsert SoftwareComponent node
            await session.run(
                """
                MERGE (c:SoftwareComponent {arxml_ref: $arxml_ref})
                SET c.name        = $name,
                    c.variant     = $variant,
                    c.description = $description
                """,
                arxml_ref=data.arxml_ref,
                name=data.name,
                variant=data.variant,
                description=data.description,
            )

            for port in data.ports:
                # Upsert Port node + HAS_PORT edge
                await session.run(
                    """
                    MERGE (p:Port {arxml_ref: $port_ref})
                    SET p.name      = $name,
                        p.direction = $direction
                    WITH p
                    MATCH (c:SoftwareComponent {arxml_ref: $swc_ref})
                    MERGE (c)-[:HAS_PORT]->(p)
                    """,
                    port_ref=port.arxml_ref,
                    name=port.name,
                    direction=port.direction,
                    swc_ref=data.arxml_ref,
                )
                edges += 1

                # Upsert Interface node + directional relationship
                rel = "REALIZES" if port.direction == "provided" else "REQUIRES_INTERFACE"
                await session.run(
                    f"""
                    MERGE (i:Interface {{arxml_ref: $iface_ref}})
                    WITH i
                    MATCH (p:Port {{arxml_ref: $port_ref}})
                    MERGE (p)-[:{rel}]->(i)
                    """,
                    iface_ref=port.interface_ref,
                    port_ref=port.arxml_ref,
                )
                edges += 1

        return edges

    async def get_component_context(self, arxml_refs: list[str]) -> str:
        """Return a text summary of the subgraph for the given ARXML refs.

        Used by the RAG pipeline to enrich retrieved chunks with graph context
        (connected ports, related interfaces) before prompt construction.
        """
        if self._driver is None or not arxml_refs:
            return ""

        rows: list[str] = []
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (c:SoftwareComponent)
                WHERE c.arxml_ref IN $refs
                OPTIONAL MATCH (c)-[:HAS_PORT]->(p:Port)
                RETURN c.name    AS name,
                       c.variant AS variant,
                       collect(p.name + ' (' + p.direction + ')') AS ports
                """,
                refs=arxml_refs,
            )
            async for record in result:
                port_list = ", ".join(record["ports"]) if record["ports"] else "none"
                rows.append(
                    f"SWC: {record['name']} ({record['variant']}) | Ports: {port_list}"
                )
        return "\n".join(rows)

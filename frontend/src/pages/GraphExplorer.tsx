/**
 * Graph Explorer — SVG visualisation of the AUTOSAR component landscape.
 *
 * Fetches all SWCs from core-api and renders them as an SVG force-inspired
 * layout. Nodes are colour-coded by variant (Classic=blue, Adaptive=orange).
 *
 * Phase 6 will connect this to the Neo4j graph-service to draw real
 * port-connection edges between components.
 */

import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { listComponents } from '../api/client'
import type { ComponentResponse } from '../api/schema'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { VariantBadge } from '../components/VariantBadge'
import { useUiStore } from '../store/ui'

// ── Layout helpers ────────────────────────────────────────────────────────────

const SVG_W = 800
const SVG_H = 500
const NODE_R = 28

type NodePosition = {
  id: string
  x: number
  y: number
  component: ComponentResponse
}

/** Arrange nodes in a simple radial layout. */
function computeLayout(components: ComponentResponse[]): NodePosition[] {
  if (components.length === 0) return []
  const cx = SVG_W / 2
  const cy = SVG_H / 2
  const r = Math.min(cx, cy) - NODE_R - 20

  return components.map((c, i) => {
    const angle = (2 * Math.PI * i) / components.length - Math.PI / 2
    return {
      id: c.id,
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
      component: c,
    }
  })
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SvgNode({
  node,
  isSelected,
  onSelect,
}: {
  node: NodePosition
  isSelected: boolean
  onSelect: (id: string) => void
}): React.ReactElement {
  const fill = node.component.variant === 'classic' ? '#3b82f6' : '#f97316'
  const stroke = isSelected ? '#1e293b' : 'transparent'

  return (
    <g
      className="graph-node"
      transform={`translate(${node.x},${node.y})`}
      onClick={() => onSelect(node.id)}
      role="button"
      aria-label={node.component.name}
      aria-pressed={isSelected}
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') onSelect(node.id)
      }}
    >
      <circle
        r={NODE_R}
        fill={fill}
        stroke={stroke}
        strokeWidth={3}
        opacity={isSelected ? 1 : 0.85}
      />
      <text
        textAnchor="middle"
        dominantBaseline="middle"
        fontSize={9}
        fill="white"
        style={{ pointerEvents: 'none', userSelect: 'none' }}
      >
        {node.component.name.replace('SWC', '').slice(0, 12)}
      </text>
    </g>
  )
}

function DetailPanel({ component }: { component: ComponentResponse }): React.ReactElement {
  return (
    <aside className="graph-detail">
      <h2 className="graph-detail__name">{component.name}</h2>
      <VariantBadge variant={component.variant} />
      <dl className="definition-list" style={{ marginTop: '0.75rem' }}>
        <dt>ARXML Ref</dt>
        <dd>
          <code>{component.arxml_ref}</code>
        </dd>
        {component.description !== undefined && (
          <>
            <dt>Description</dt>
            <dd>{component.description}</dd>
          </>
        )}
      </dl>
      <p className="text-muted" style={{ marginTop: '1rem', fontSize: '0.75rem' }}>
        Port-connection edges will appear in Phase 6 once the graph-service
        Neo4j backend is wired to core-api.
      </p>
    </aside>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function GraphExplorer(): React.ReactElement {
  const { selectedComponentId, setSelectedComponent } = useUiStore()
  const [hoveredId, setHoveredId] = useState<string | null>(null)

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['components', null, undefined],
    queryFn: () => listComponents({ page_size: 50 }),
  })

  const nodes = useMemo(
    () => computeLayout(data?.components ?? []),
    [data?.components],
  )

  const selectedComponent = useMemo(
    () => data?.components.find((c) => c.id === selectedComponentId),
    [data?.components, selectedComponentId],
  )

  const hoveredComponent = useMemo(
    () => data?.components.find((c) => c.id === hoveredId),
    [data?.components, hoveredId],
  )

  const displayComponent = selectedComponent ?? hoveredComponent

  return (
    <main className="page graph-explorer">
      <header className="page__header">
        <h1>Component Graph Explorer</h1>
        <p className="page__subtitle">
          {data !== undefined ? `${data.total_count} SWCs` : '\u00a0'} — click a node for
          details
        </p>
      </header>

      {isLoading && <LoadingSpinner />}

      {isError && (
        <div role="alert" className="error-banner">
          {error instanceof Error ? error.message : 'Failed to load graph data'}
        </div>
      )}

      {data !== undefined && (
        <div className="graph-layout">
          <svg
            className="graph-svg"
            viewBox={`0 0 ${SVG_W} ${SVG_H}`}
            aria-label="Component relationship graph"
            role="img"
          >
            <defs>
              <radialGradient id="bg-grad" cx="50%" cy="50%">
                <stop offset="0%" stopColor="#1e293b" />
                <stop offset="100%" stopColor="#0f172a" />
              </radialGradient>
            </defs>
            <rect width={SVG_W} height={SVG_H} fill="url(#bg-grad)" rx={8} />

            {nodes.map((node) => (
              <SvgNode
                key={node.id}
                node={node}
                isSelected={node.id === selectedComponentId}
                onSelect={(id) => {
                  setSelectedComponent(id === selectedComponentId ? null : id)
                }}
              />
            ))}
          </svg>

          {displayComponent !== undefined ? (
            <DetailPanel component={displayComponent} />
          ) : (
            <aside className="graph-detail graph-detail--empty">
              <p className="text-muted">Select a node to view details.</p>
              <div className="graph-legend">
                <span className="legend-dot legend-dot--classic" /> Classic
                <span className="legend-dot legend-dot--adaptive" /> Adaptive
              </div>
            </aside>
          )}
        </div>
      )}
    </main>
  )
}

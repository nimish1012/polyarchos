/**
 * Component Browser — paginated, filterable list of all AUTOSAR SWCs.
 *
 * Uses TanStack Query for server state. No useEffect + useState data fetching.
 */

import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { listComponents } from '../api/client'
import type { AutosarVariant, ComponentResponse } from '../api/schema'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { VariantBadge } from '../components/VariantBadge'
import { useUiStore } from '../store/ui'

// ── Sub-components ────────────────────────────────────────────────────────────

function ComponentRow({ component }: { component: ComponentResponse }): React.ReactElement {
  const { selectedComponentId, setSelectedComponent } = useUiStore()
  const isSelected = selectedComponentId === component.id

  return (
    <tr
      className={`component-row${isSelected ? ' component-row--selected' : ''}`}
      onClick={() => setSelectedComponent(isSelected ? null : component.id)}
      aria-selected={isSelected}
      role="row"
      style={{ cursor: 'pointer' }}
    >
      <td>{component.name}</td>
      <td>
        <VariantBadge variant={component.variant} />
      </td>
      <td>
        <code>{component.arxml_ref}</code>
      </td>
      <td>{component.description ?? <span className="text-muted">—</span>}</td>
    </tr>
  )
}

function VariantFilter({
  value,
  onChange,
}: {
  value: AutosarVariant | null
  onChange: (v: AutosarVariant | null) => void
}): React.ReactElement {
  return (
    <fieldset className="variant-filter">
      <legend className="sr-only">Filter by variant</legend>
      {(['classic', 'adaptive'] as const).map((v) => (
        <label key={v} className="variant-filter__option">
          <input
            type="radio"
            name="variant"
            value={v}
            checked={value === v}
            onChange={() => onChange(v)}
          />
          <VariantBadge variant={v} />
        </label>
      ))}
      <label className="variant-filter__option">
        <input
          type="radio"
          name="variant"
          value=""
          checked={value === null}
          onChange={() => onChange(null)}
        />
        All
      </label>
    </fieldset>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function ComponentBrowser(): React.ReactElement {
  const { variantFilter, setVariantFilter } = useUiStore()
  const [pageToken, setPageToken] = useState<string | undefined>(undefined)

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['components', variantFilter, pageToken],
    queryFn: () =>
      listComponents({
        page_size: 20,
        ...(pageToken !== undefined && { page_token: pageToken }),
        ...(variantFilter !== null && { variant: variantFilter }),
      }),
  })

  return (
    <main className="page component-browser">
      <header className="page__header">
        <h1>Component Browser</h1>
        <p className="page__subtitle">
          {data !== undefined ? `${data.total_count} SWCs indexed` : '\u00a0'}
        </p>
      </header>

      <VariantFilter value={variantFilter} onChange={setVariantFilter} />

      {isLoading && <LoadingSpinner />}

      {isError && (
        <div role="alert" className="error-banner">
          {error instanceof Error ? error.message : 'Failed to load components'}
        </div>
      )}

      {data !== undefined && (
        <>
          <table className="component-table" role="grid" aria-label="Software components">
            <thead>
              <tr role="row">
                <th scope="col">Name</th>
                <th scope="col">Variant</th>
                <th scope="col">ARXML Ref</th>
                <th scope="col">Description</th>
              </tr>
            </thead>
            <tbody>
              {data.components.map((c) => (
                <ComponentRow key={c.id} component={c} />
              ))}
            </tbody>
          </table>

          <div className="pagination">
            <button
              type="button"
              disabled={pageToken === undefined}
              onClick={() => setPageToken(undefined)}
            >
              ← First
            </button>
            <button
              type="button"
              disabled={data.next_page_token === undefined}
              onClick={() => setPageToken(data.next_page_token)}
            >
              Next →
            </button>
          </div>
        </>
      )}
    </main>
  )
}

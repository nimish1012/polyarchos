/**
 * Semantic Search — natural-language Q&A over the AUTOSAR component graph.
 *
 * Uses TanStack Query mutation so the search isn't triggered on page load.
 * Recent queries are persisted in Zustand (client state, not server state).
 */

import { useMutation } from '@tanstack/react-query'
import { useRef, useState } from 'react'
import { searchComponents } from '../api/client'
import type { SearchResponse } from '../api/schema'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { VariantBadge } from '../components/VariantBadge'
import { useUiStore } from '../store/ui'

function ResultCard({
  result,
}: {
  result: SearchResponse['results'][number]
}): React.ReactElement {
  return (
    <article className="result-card">
      <header className="result-card__header">
        <span className="result-card__name">{result.component.name}</span>
        <VariantBadge variant={result.component.variant} />
        <span className="result-card__score" title="Cosine similarity">
          {(result.score * 100).toFixed(1)}%
        </span>
      </header>
      <p className="result-card__ref">
        <code>{result.component.arxml_ref}</code>
      </p>
      {result.component.description !== undefined && (
        <p className="result-card__description">{result.component.description}</p>
      )}
    </article>
  )
}

export function SemanticSearch(): React.ReactElement {
  const [query, setQuery] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const { searchHistory, pushSearchHistory, clearSearchHistory } = useUiStore()

  const mutation = useMutation({
    mutationFn: (q: string) => searchComponents({ query: q, top_k: 10 }),
  })

  function handleSubmit(q: string): void {
    const trimmed = q.trim()
    if (trimmed.length === 0) return
    pushSearchHistory(trimmed)
    mutation.mutate(trimmed)
  }

  return (
    <main className="page semantic-search">
      <header className="page__header">
        <h1>Semantic Search</h1>
        <p className="page__subtitle">
          Ask a natural-language question about the AUTOSAR component landscape.
        </p>
      </header>

      <form
        className="search-form"
        onSubmit={(e) => {
          e.preventDefault()
          handleSubmit(query)
        }}
      >
        <input
          ref={inputRef}
          className="search-form__input"
          type="search"
          placeholder='e.g. "Which SWCs control brake pressure?"'
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Search query"
        />
        <button type="submit" className="search-form__btn" disabled={mutation.isPending}>
          Search
        </button>
      </form>

      {searchHistory.length > 0 && (
        <aside className="search-history">
          <span className="search-history__label">Recent:</span>
          {searchHistory.map((q) => (
            <button
              key={q}
              type="button"
              className="search-history__chip"
              onClick={() => {
                setQuery(q)
                handleSubmit(q)
              }}
            >
              {q}
            </button>
          ))}
          <button
            type="button"
            className="search-history__clear"
            onClick={clearSearchHistory}
          >
            Clear
          </button>
        </aside>
      )}

      {mutation.isPending && <LoadingSpinner />}

      {mutation.isError && (
        <div role="alert" className="error-banner">
          {mutation.error instanceof Error ? mutation.error.message : 'Search failed'}
        </div>
      )}

      {mutation.data !== undefined && (
        <section aria-label="Search results">
          {mutation.data.results.length === 0 ? (
            <p className="text-muted">No results found.</p>
          ) : (
            <ol className="result-list" role="list">
              {mutation.data.results.map((r, i) => (
                // biome-ignore lint: index key acceptable for immutable search results
                <li key={i}>
                  <ResultCard result={r} />
                </li>
              ))}
            </ol>
          )}
        </section>
      )}
    </main>
  )
}

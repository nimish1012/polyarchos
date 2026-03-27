/**
 * API Playground — interactive REST API explorer backed by the core-api OpenAPI spec.
 *
 * Lets engineers hand-craft requests to any core-api endpoint and inspect
 * the raw JSON response. No auth tokens in this dev-only tool.
 */

import { useState } from 'react'
import { LoadingSpinner } from '../components/LoadingSpinner'

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE'

type RequestState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; body: string; statusCode: number; durationMs: number }
  | { status: 'error'; message: string }

const PRESET_REQUESTS = [
  {
    label: 'List SWCs (first 20)',
    method: 'GET' as HttpMethod,
    path: '/api/v1/components?page_size=20',
    body: '',
  },
  {
    label: 'List Classic SWCs',
    method: 'GET' as HttpMethod,
    path: '/api/v1/components?variant=classic&page_size=10',
    body: '',
  },
  {
    label: 'List Adaptive SWCs',
    method: 'GET' as HttpMethod,
    path: '/api/v1/components?variant=adaptive&page_size=10',
    body: '',
  },
  {
    label: 'Semantic search',
    method: 'POST' as HttpMethod,
    path: '/api/v1/search',
    body: JSON.stringify({ query: 'brake pressure control', top_k: 5 }, null, 2),
  },
  {
    label: 'Health check',
    method: 'GET' as HttpMethod,
    path: '/api/v1/health',
    body: '',
  },
] as const

export function ApiPlayground(): React.ReactElement {
  const [method, setMethod] = useState<HttpMethod>('GET')
  const [path, setPath] = useState('/api/v1/components?page_size=20')
  const [bodyText, setBodyText] = useState('')
  const [state, setState] = useState<RequestState>({ status: 'idle' })

  function applyPreset(preset: (typeof PRESET_REQUESTS)[number]): void {
    setMethod(preset.method)
    setPath(preset.path)
    setBodyText(preset.body)
  }

  async function handleSend(): Promise<void> {
    setState({ status: 'loading' })
    const start = performance.now()

    try {
      const init: RequestInit = { method }
      if (bodyText.trim().length > 0 && method !== 'GET' && method !== 'DELETE') {
        init.body = bodyText
        init.headers = { 'Content-Type': 'application/json' }
      }

      const res = await fetch(path, init)
      const text = await res.text()
      const durationMs = Math.round(performance.now() - start)

      // Pretty-print JSON if possible.
      let formatted = text
      try {
        formatted = JSON.stringify(JSON.parse(text), null, 2)
      } catch {
        // Not JSON — display raw.
      }

      setState({ status: 'success', body: formatted, statusCode: res.status, durationMs })
    } catch (err) {
      setState({
        status: 'error',
        message: err instanceof Error ? err.message : 'Request failed',
      })
    }
  }

  const canSend = path.trim().length > 0 && state.status !== 'loading'

  return (
    <main className="page api-playground">
      <header className="page__header">
        <h1>API Playground</h1>
        <p className="page__subtitle">
          Explore the core-api REST endpoints directly from the browser.
        </p>
      </header>

      <section className="playground-presets" aria-label="Preset requests">
        <span className="playground-presets__label">Presets:</span>
        {PRESET_REQUESTS.map((p) => (
          <button
            key={p.label}
            type="button"
            className="preset-chip"
            onClick={() => applyPreset(p)}
          >
            {p.label}
          </button>
        ))}
      </section>

      <div className="playground-layout">
        <section className="playground-request" aria-label="Request builder">
          <div className="request-line">
            <select
              className="method-select"
              value={method}
              onChange={(e) => setMethod(e.target.value as HttpMethod)}
              aria-label="HTTP method"
            >
              {(['GET', 'POST', 'PUT', 'DELETE'] as const).map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
            <input
              className="path-input"
              type="text"
              value={path}
              onChange={(e) => setPath(e.target.value)}
              placeholder="/api/v1/..."
              aria-label="Request path"
              spellCheck={false}
            />
            <button
              type="button"
              className="btn btn--primary"
              onClick={() => void handleSend()}
              disabled={!canSend}
            >
              Send
            </button>
          </div>

          {method !== 'GET' && method !== 'DELETE' && (
            <div className="request-body">
              <label htmlFor="request-body" className="form-label">
                Request Body (JSON)
              </label>
              <textarea
                id="request-body"
                className="body-textarea"
                value={bodyText}
                onChange={(e) => setBodyText(e.target.value)}
                rows={8}
                spellCheck={false}
                placeholder='{"query": "...", "top_k": 5}'
              />
            </div>
          )}
        </section>

        <section className="playground-response" aria-label="Response" aria-live="polite">
          {state.status === 'loading' && <LoadingSpinner />}

          {state.status === 'idle' && (
            <p className="text-muted">Send a request to see the response.</p>
          )}

          {state.status === 'error' && (
            <div role="alert" className="error-banner">
              {state.message}
            </div>
          )}

          {state.status === 'success' && (
            <>
              <div className="response-meta">
                <span
                  className={`status-badge status-badge--${state.statusCode < 300 ? 'ok' : 'err'}`}
                >
                  {state.statusCode}
                </span>
                <span className="text-muted response-meta__duration">
                  {state.durationMs} ms
                </span>
              </div>
              <pre className="response-body">{state.body}</pre>
            </>
          )}
        </section>
      </div>
    </main>
  )
}

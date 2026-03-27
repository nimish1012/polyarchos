/**
 * Type-safe REST API client for core-api.
 *
 * All responses are validated at runtime with Zod schemas so a mismatch
 * between the server and client surfaces as a thrown error, not silent data
 * corruption. All types flow from schema.ts — never hand-written.
 */

import { z } from 'zod'
import {
  ListComponentsQuery,
  ListComponentsResponseSchema,
  SearchRequest,
  SearchResponseSchema,
  type ListComponentsResponse,
  type SearchResponse,
} from './schema'

// ── Config ────────────────────────────────────────────────────────────────────

const BASE = '/api/v1'

// ── Helpers ───────────────────────────────────────────────────────────────────

class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(
  path: string,
  schema: z.ZodType<T>,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })

  if (!res.ok) {
    const body: unknown = await res.json().catch(() => ({}))
    const message =
      typeof body === 'object' &&
      body !== null &&
      'error' in body &&
      typeof body.error === 'string'
        ? body.error
        : `HTTP ${res.status}`
    throw new ApiError(message, res.status)
  }

  const json: unknown = await res.json()
  return schema.parse(json)
}

function buildQuery(params: Record<string, string | number | undefined>): string {
  const entries = Object.entries(params).filter(
    (pair): pair is [string, string | number] => pair[1] !== undefined,
  )
  if (entries.length === 0) return ''
  const qs = new URLSearchParams(
    entries.map(([k, v]) => [k, String(v)]),
  ).toString()
  return `?${qs}`
}

// ── API calls ─────────────────────────────────────────────────────────────────

export function listComponents(query: ListComponentsQuery = {}): Promise<ListComponentsResponse> {
  const qs = buildQuery({
    page_size: query.page_size,
    page_token: query.page_token,
    variant: query.variant,
  })
  return request(`/components${qs}`, ListComponentsResponseSchema)
}

export function searchComponents(body: SearchRequest): Promise<SearchResponse> {
  return request('/components/search', SearchResponseSchema, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export { ApiError }

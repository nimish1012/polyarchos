import { describe, expect, it } from 'vitest'
import {
  ComponentResponseSchema,
  ListComponentsResponseSchema,
  SearchResponseSchema,
} from '../api/schema'

describe('ComponentResponseSchema', () => {
  it('parses a valid classic component', () => {
    const raw = {
      id: '123e4567-e89b-12d3-a456-426614174000',
      arxml_ref: '/MyECU/EngineControlSWC',
      name: 'EngineControlSWC',
      variant: 'classic',
    }
    const result = ComponentResponseSchema.safeParse(raw)
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data.variant).toBe('classic')
      expect(result.data.description).toBeUndefined()
    }
  })

  it('parses a component with optional description', () => {
    const raw = {
      id: '123e4567-e89b-12d3-a456-426614174000',
      arxml_ref: '/MyECU/BrakeSWC',
      name: 'BrakeSWC',
      variant: 'adaptive',
      description: 'Brake control component',
    }
    const result = ComponentResponseSchema.safeParse(raw)
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data.description).toBe('Brake control component')
    }
  })

  it('rejects an invalid variant', () => {
    const raw = {
      id: '123e4567-e89b-12d3-a456-426614174000',
      arxml_ref: '/MyECU/Foo',
      name: 'Foo',
      variant: 'unknown',
    }
    expect(ComponentResponseSchema.safeParse(raw).success).toBe(false)
  })

  it('rejects missing required fields', () => {
    expect(ComponentResponseSchema.safeParse({ name: 'Foo' }).success).toBe(false)
  })
})

describe('ListComponentsResponseSchema', () => {
  it('parses a page with no next token', () => {
    const raw = {
      components: [
        {
          id: '123e4567-e89b-12d3-a456-426614174000',
          arxml_ref: '/MyECU/SWC1',
          name: 'SWC1',
          variant: 'classic',
        },
      ],
      total_count: 1,
    }
    const result = ListComponentsResponseSchema.safeParse(raw)
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data.components).toHaveLength(1)
      expect(result.data.next_page_token).toBeUndefined()
    }
  })

  it('parses a page with a next token', () => {
    const raw = {
      components: [],
      total_count: 100,
      next_page_token: 'eyJvZmZzZXQiOjIwfQ==',
    }
    const result = ListComponentsResponseSchema.safeParse(raw)
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data.next_page_token).toBe('eyJvZmZzZXQiOjIwfQ==')
    }
  })
})

describe('SearchResponseSchema', () => {
  it('parses search results with scores', () => {
    const raw = {
      results: [
        {
          component: {
            id: '123e4567-e89b-12d3-a456-426614174000',
            arxml_ref: '/MyECU/BrakeSWC',
            name: 'BrakeSWC',
            variant: 'classic',
          },
          score: 0.92,
        },
      ],
    }
    const result = SearchResponseSchema.safeParse(raw)
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data.results[0]?.score).toBe(0.92)
    }
  })

  it('rejects a score outside [0, 1]', () => {
    const raw = {
      results: [
        {
          component: {
            id: '123e4567-e89b-12d3-a456-426614174000',
            arxml_ref: '/MyECU/BrakeSWC',
            name: 'BrakeSWC',
            variant: 'classic',
          },
          score: 1.5,
        },
      ],
    }
    expect(SearchResponseSchema.safeParse(raw).success).toBe(false)
  })
})

/**
 * Client-side UI state managed by Zustand.
 *
 * Only ephemeral UI state lives here (selected component, search history).
 * All server state is managed by TanStack Query — never duplicated here.
 */

import { create } from 'zustand'
import type { AutosarVariant } from '../api/schema'

type UiState = {
  /** The currently selected component ID, or null if nothing is selected. */
  selectedComponentId: string | null
  /** Active variant filter on the component browser page. */
  variantFilter: AutosarVariant | null
  /** Recent search queries (most-recent first, capped at 10). */
  searchHistory: string[]

  setSelectedComponent: (id: string | null) => void
  setVariantFilter: (variant: AutosarVariant | null) => void
  pushSearchHistory: (query: string) => void
  clearSearchHistory: () => void
}

export const useUiStore = create<UiState>((set) => ({
  selectedComponentId: null,
  variantFilter: null,
  searchHistory: [],

  setSelectedComponent: (id) => set({ selectedComponentId: id }),

  setVariantFilter: (variant) => set({ variantFilter: variant }),

  pushSearchHistory: (query) =>
    set((state) => ({
      searchHistory: [query, ...state.searchHistory.filter((q) => q !== query)].slice(0, 10),
    })),

  clearSearchHistory: () => set({ searchHistory: [] }),
}))

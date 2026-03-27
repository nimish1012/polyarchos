import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as clientModule from '../api/client'
import { ComponentBrowser } from '../pages/ComponentBrowser'

vi.mock('../api/client')

function renderWithProviders(ui: React.ReactElement): ReturnType<typeof render> {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  )
}

const MOCK_RESPONSE = {
  components: [
    {
      id: '123e4567-e89b-12d3-a456-426614174000',
      arxml_ref: '/MyECU/EngineControlSWC',
      name: 'EngineControlSWC',
      variant: 'classic' as const,
      description: 'Engine control',
    },
    {
      id: '223e4567-e89b-12d3-a456-426614174001',
      arxml_ref: '/MyECU/PerceptionSWC',
      name: 'PerceptionSWC',
      variant: 'adaptive' as const,
    },
  ],
  total_count: 2,
  next_page_token: undefined,
}

describe('ComponentBrowser', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading state initially', () => {
    vi.mocked(clientModule.listComponents).mockReturnValue(new Promise(() => {}))
    renderWithProviders(<ComponentBrowser />)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('renders component rows after data loads', async () => {
    vi.mocked(clientModule.listComponents).mockResolvedValue(MOCK_RESPONSE)

    renderWithProviders(<ComponentBrowser />)

    await waitFor(() => {
      expect(screen.getByText('EngineControlSWC')).toBeInTheDocument()
      expect(screen.getByText('PerceptionSWC')).toBeInTheDocument()
    })
  })

  it('displays total count in subtitle', async () => {
    vi.mocked(clientModule.listComponents).mockResolvedValue(MOCK_RESPONSE)

    renderWithProviders(<ComponentBrowser />)

    await waitFor(() => {
      expect(screen.getByText(/2 swcs indexed/i)).toBeInTheDocument()
    })
  })

  it('shows error banner on failure', async () => {
    vi.mocked(clientModule.listComponents).mockRejectedValue(new Error('Network error'))

    renderWithProviders(<ComponentBrowser />)

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
      expect(screen.getByText(/network error/i)).toBeInTheDocument()
    })
  })

  it('disables Next button when there is no next_page_token', async () => {
    vi.mocked(clientModule.listComponents).mockResolvedValue(MOCK_RESPONSE)

    renderWithProviders(<ComponentBrowser />)

    await waitFor(() => screen.getByText('EngineControlSWC'))

    const nextBtn = screen.getByRole('button', { name: /next/i })
    expect(nextBtn).toBeDisabled()
  })

  it('enables Next button when next_page_token is present', async () => {
    vi.mocked(clientModule.listComponents).mockResolvedValue({
      ...MOCK_RESPONSE,
      next_page_token: 'tok123',
    })

    renderWithProviders(<ComponentBrowser />)

    await waitFor(() => screen.getByText('EngineControlSWC'))

    const nextBtn = screen.getByRole('button', { name: /next/i })
    expect(nextBtn).not.toBeDisabled()
  })

  it('passes variant filter to the API call', async () => {
    vi.mocked(clientModule.listComponents).mockResolvedValue(MOCK_RESPONSE)

    renderWithProviders(<ComponentBrowser />)

    await waitFor(() => screen.getByText('EngineControlSWC'))

    const classicRadio = screen.getByRole('radio', { name: /classic/i })
    await userEvent.click(classicRadio)

    await waitFor(() => {
      expect(clientModule.listComponents).toHaveBeenCalledWith(
        expect.objectContaining({ variant: 'classic' }),
      )
    })
  })
})

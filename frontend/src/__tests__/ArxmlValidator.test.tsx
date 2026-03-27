import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ArxmlValidator } from '../pages/ArxmlValidator'
import * as loaderModule from '../wasm/loader'

// Mock the WASM loader so tests don't need a built WASM binary.
vi.mock('../wasm/loader')

const mockWasm = {
  version: () => '0.1.0',
  parse_arxml_component: vi.fn(),
  validate_component: vi.fn(),
}

describe('ArxmlValidator', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading text while WASM loads', () => {
    // loadWasm returns a promise that never resolves in this test.
    vi.mocked(loaderModule.loadWasm).mockReturnValue(new Promise(() => {}))
    render(<ArxmlValidator />)
    expect(screen.getByText(/loading wasm module/i)).toBeInTheDocument()
  })

  it('shows ready message when WASM loads successfully', async () => {
    vi.mocked(loaderModule.loadWasm).mockResolvedValue({
      status: 'ok',
      module: mockWasm as unknown as loaderModule.WasmModule,
    })

    render(<ArxmlValidator />)

    await waitFor(() => {
      expect(screen.getByText(/wasm module ready/i)).toBeInTheDocument()
    })
  })

  it('shows a warning banner when WASM is unavailable', async () => {
    vi.mocked(loaderModule.loadWasm).mockResolvedValue({
      status: 'unavailable',
      reason: 'Module not found',
    })

    render(<ArxmlValidator />)

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
      expect(screen.getByText(/wasm module not available/i)).toBeInTheDocument()
    })
  })

  it('displays parse result on successful validation', async () => {
    const parseResult = {
      component: {
        name: 'EngineControlSWC',
        arxml_ref: '/MyECU/EngineControlSWC',
        variant: 'classic',
      },
      ports: [
        {
          name: 'FuelPort',
          arxml_ref: '/MyECU/EngineControlSWC/FuelPort',
          direction: 'provided',
          interface_ref: '/Interfaces/FuelIf',
        },
      ],
    }

    mockWasm.parse_arxml_component.mockReturnValue(JSON.stringify(parseResult))

    vi.mocked(loaderModule.loadWasm).mockResolvedValue({
      status: 'ok',
      module: mockWasm as unknown as loaderModule.WasmModule,
    })

    render(<ArxmlValidator />)

    await waitFor(() => {
      expect(screen.getByText(/wasm module ready/i)).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: /validate/i }))

    await waitFor(() => {
      expect(screen.getByText('EngineControlSWC')).toBeInTheDocument()
      expect(screen.getByText('/MyECU/EngineControlSWC')).toBeInTheDocument()
    })
  })

  it('shows error when WASM parse throws', async () => {
    mockWasm.parse_arxml_component.mockImplementation(() => {
      throw new Error('Invalid ARXML')
    })

    vi.mocked(loaderModule.loadWasm).mockResolvedValue({
      status: 'ok',
      module: mockWasm as unknown as loaderModule.WasmModule,
    })

    render(<ArxmlValidator />)

    await waitFor(() => screen.getByText(/wasm module ready/i))

    await userEvent.click(screen.getByRole('button', { name: /validate/i }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
      expect(screen.getByText(/invalid arxml/i)).toBeInTheDocument()
    })
  })
})

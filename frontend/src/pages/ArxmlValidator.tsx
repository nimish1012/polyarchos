/**
 * ARXML Validator — in-browser ARXML parsing and validation using the WASM module.
 *
 * No server round-trip. The polyarchos WASM module (wasm/pkg/) is loaded once
 * and used directly in the browser. Demonstrates the WASM API surface from Phase 3.
 */

import { useEffect, useRef, useState } from 'react'
import { loadWasm, type WasmModule } from '../wasm/loader'

const SAMPLE_ARXML = `<?xml version="1.0" encoding="UTF-8"?>
<AUTOSAR>
  <AR-PACKAGES>
    <AR-PACKAGE>
      <SHORT-NAME>MyECU</SHORT-NAME>
      <ELEMENTS>
        <APPLICATION-SW-COMPONENT-TYPE>
          <SHORT-NAME>EngineControlSWC</SHORT-NAME>
          <LONG-NAME>Engine Control Software Component</LONG-NAME>
          <PORTS>
            <P-PORT-PROTOTYPE>
              <SHORT-NAME>FuelInjectionPort</SHORT-NAME>
              <PROVIDED-INTERFACE-TREF>/Interfaces/FuelInjectionIf</PROVIDED-INTERFACE-TREF>
            </P-PORT-PROTOTYPE>
          </PORTS>
        </APPLICATION-SW-COMPONENT-TYPE>
      </ELEMENTS>
    </AR-PACKAGE>
  </AR-PACKAGES>
</AUTOSAR>`

type ParsedResult = {
  component: {
    name: string
    arxml_ref: string
    variant: string
    description?: string
  }
  ports: Array<{
    name: string
    arxml_ref: string
    direction: string
    interface_ref: string
  }>
}

type ValidatorState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'wasm-unavailable'; reason: string }
  | { status: 'success'; result: ParsedResult; wasmVersion: string }
  | { status: 'error'; message: string }

export function ArxmlValidator(): React.ReactElement {
  const [arxml, setArxml] = useState(SAMPLE_ARXML)
  const [state, setState] = useState<ValidatorState>({ status: 'idle' })
  const wasmRef = useRef<WasmModule | null>(null)

  // Attempt to load WASM on mount; don't block rendering.
  useEffect(() => {
    setState({ status: 'loading' })
    void loadWasm().then((result) => {
      if (result.status === 'unavailable') {
        setState({ status: 'wasm-unavailable', reason: result.reason })
      } else {
        wasmRef.current = result.module
        setState({ status: 'idle' })
      }
    })
  }, [])

  function handleValidate(): void {
    const wasm = wasmRef.current
    if (wasm === null) return

    try {
      const raw: unknown = JSON.parse(wasm.parse_arxml_component(arxml))
      // Runtime shape check before trusting the WASM output.
      if (
        typeof raw !== 'object' ||
        raw === null ||
        !('component' in raw) ||
        !('ports' in raw)
      ) {
        throw new Error('Unexpected WASM output shape')
      }
      setState({ status: 'success', result: raw as ParsedResult, wasmVersion: wasm.version() })
    } catch (err) {
      setState({
        status: 'error',
        message: err instanceof Error ? err.message : 'Validation failed',
      })
    }
  }

  const canValidate = wasmRef.current !== null && arxml.trim().length > 0

  return (
    <main className="page arxml-validator">
      <header className="page__header">
        <h1>ARXML Validator</h1>
        <p className="page__subtitle">
          Parse and validate ARXML components in-browser using the polyarchos WASM module.
          Zero server round-trip.
        </p>
      </header>

      {state.status === 'wasm-unavailable' && (
        <div role="alert" className="warning-banner">
          <strong>WASM module not available.</strong> Run{' '}
          <code>wasm-pack build wasm/ --target web</code> to build it.
          <details>
            <summary>Details</summary>
            <pre>{state.reason}</pre>
          </details>
        </div>
      )}

      <div className="validator-layout">
        <div className="validator-input">
          <label htmlFor="arxml-input" className="form-label">
            ARXML Input
          </label>
          <textarea
            id="arxml-input"
            className="arxml-textarea"
            value={arxml}
            onChange={(e) => setArxml(e.target.value)}
            rows={20}
            spellCheck={false}
            aria-label="ARXML document input"
          />
          <div className="validator-actions">
            <button
              type="button"
              className="btn btn--primary"
              onClick={handleValidate}
              disabled={!canValidate}
            >
              Validate
            </button>
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => setArxml(SAMPLE_ARXML)}
            >
              Load sample
            </button>
          </div>
        </div>

        <div className="validator-output" aria-live="polite">
          {state.status === 'loading' && (
            <p className="text-muted">Loading WASM module…</p>
          )}

          {state.status === 'idle' && wasmRef.current !== null && (
            <p className="text-muted">
              WASM module ready (v{wasmRef.current.version()}). Press Validate.
            </p>
          )}

          {state.status === 'error' && (
            <div role="alert" className="error-banner">
              <strong>Parse error:</strong> {state.message}
            </div>
          )}

          {state.status === 'success' && (
            <div className="parse-result">
              <p className="parse-result__meta">
                Parsed with WASM module v{state.wasmVersion}
              </p>
              <section>
                <h2 className="parse-result__section-title">Component</h2>
                <dl className="definition-list">
                  <dt>Name</dt>
                  <dd>{state.result.component.name}</dd>
                  <dt>ARXML Ref</dt>
                  <dd><code>{state.result.component.arxml_ref}</code></dd>
                  <dt>Variant</dt>
                  <dd>
                    <span className={`variant-badge variant-badge--${state.result.component.variant}`}>
                      {state.result.component.variant}
                    </span>
                  </dd>
                  {state.result.component.description !== undefined && (
                    <>
                      <dt>Description</dt>
                      <dd>{state.result.component.description}</dd>
                    </>
                  )}
                </dl>
              </section>

              {state.result.ports.length > 0 && (
                <section>
                  <h2 className="parse-result__section-title">
                    Ports ({state.result.ports.length})
                  </h2>
                  <table className="ports-table">
                    <thead>
                      <tr>
                        <th scope="col">Name</th>
                        <th scope="col">Direction</th>
                        <th scope="col">Interface</th>
                      </tr>
                    </thead>
                    <tbody>
                      {state.result.ports.map((port) => (
                        <tr key={port.arxml_ref}>
                          <td>{port.name}</td>
                          <td>
                            <span className={`direction-badge direction-badge--${port.direction}`}>
                              {port.direction}
                            </span>
                          </td>
                          <td><code>{port.interface_ref}</code></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </section>
              )}
            </div>
          )}
        </div>
      </div>
    </main>
  )
}

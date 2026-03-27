/**
 * Lazy loader for the polyarchos WASM module.
 *
 * The WASM pkg (wasm/pkg/) is gitignored and generated at build time by
 * `wasm-pack build wasm/ --target web`. This module loads it once and caches
 * the result. Returns null gracefully if the module is not available
 * (e.g. in test environments or before wasm-pack has been run).
 */

export type WasmModule = {
  parse_arxml_component: (xml: string) => string
  validate_component: (json: string) => void
  classify_variant: (arxml_path: string) => string
  resolve_port_connections: (ports_json: string) => string
  version: () => string
}

export type LoadResult =
  | { status: 'ok'; module: WasmModule }
  | { status: 'unavailable'; reason: string }

let _cached: LoadResult | null = null

export async function loadWasm(): Promise<LoadResult> {
  if (_cached !== null) return _cached

  try {
    // @ts-expect-error — generated at build time, not committed; path resolves at runtime.
    const mod = (await import(/* @vite-ignore */ '../../wasm/pkg/polyarchos_wasm.js')) as {
      default: () => Promise<void>
    } & WasmModule

    await mod.default()
    _cached = { status: 'ok', module: mod }
  } catch (err) {
    const reason =
      err instanceof Error ? err.message : 'Unknown error loading WASM module'
    _cached = { status: 'unavailable', reason }
  }

  return _cached
}

/** Reset the cached result. Used in tests to force a fresh load attempt. */
export function _resetWasmCache(): void {
  _cached = null
}

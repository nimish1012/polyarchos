import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import wasm from 'vite-plugin-wasm'
import topLevelAwait from 'vite-plugin-top-level-await'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    // wasm + topLevelAwait must come before react()
    wasm(),
    topLevelAwait(),
    react(),
  ],

  server: {
    // Proxy REST API calls to core-api so the browser avoids CORS issues in dev.
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
    // Allow Vite to serve files from the sibling wasm/pkg/ directory.
    fs: {
      allow: ['..'],
    },
  },

  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./vitest.setup.ts'],
    // Exclude e2e tests and the wasm pkg directory.
    exclude: ['**/node_modules/**', '**/wasm/pkg/**'],
    // Alias the wasm-pack output to a no-op stub so tests don't need a built binary.
    alias: {
      '../../wasm/pkg/polyarchos_wasm.js': '/src/__mocks__/wasmStub.ts',
    },
  },
})

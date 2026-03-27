import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { ErrorBoundary } from './components/ErrorBoundary'
import { NavBar } from './components/NavBar'
import { ApiPlayground } from './pages/ApiPlayground'
import { ArxmlValidator } from './pages/ArxmlValidator'
import { ComponentBrowser } from './pages/ComponentBrowser'
import { GraphExplorer } from './pages/GraphExplorer'
import { SemanticSearch } from './pages/SemanticSearch'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
})

export function App(): React.ReactElement {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <NavBar />
        <Routes>
          <Route path="/" element={<Navigate to="/components" replace />} />
          <Route
            path="/components"
            element={
              <ErrorBoundary>
                <ComponentBrowser />
              </ErrorBoundary>
            }
          />
          <Route
            path="/graph"
            element={
              <ErrorBoundary>
                <GraphExplorer />
              </ErrorBoundary>
            }
          />
          <Route
            path="/search"
            element={
              <ErrorBoundary>
                <SemanticSearch />
              </ErrorBoundary>
            }
          />
          <Route
            path="/validate"
            element={
              <ErrorBoundary>
                <ArxmlValidator />
              </ErrorBoundary>
            }
          />
          <Route
            path="/playground"
            element={
              <ErrorBoundary>
                <ApiPlayground />
              </ErrorBoundary>
            }
          />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

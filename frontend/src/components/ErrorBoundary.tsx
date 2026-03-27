/**
 * Route-level error boundary.
 *
 * CLAUDE.md requires every route-level component to be wrapped in an error
 * boundary. This component catches thrown errors during render and displays
 * a fallback UI instead of crashing the whole app.
 */

import { Component, type ErrorInfo, type ReactNode } from 'react'

type Props = {
  children: ReactNode
  fallback?: (error: Error) => ReactNode
}

type State =
  | { hasError: false }
  | { hasError: true; error: Error }

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: unknown): State {
    return {
      hasError: true,
      error: error instanceof Error ? error : new Error(String(error)),
    }
  }

  override componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  override render(): ReactNode {
    if (this.state.hasError) {
      const { error } = this.state
      const { fallback } = this.props
      if (fallback !== undefined) return fallback(error)
      return (
        <div role="alert" className="error-boundary">
          <h2>Something went wrong</h2>
          <pre>{error.message}</pre>
          <button
            type="button"
            onClick={() => this.setState({ hasError: false })}
          >
            Try again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

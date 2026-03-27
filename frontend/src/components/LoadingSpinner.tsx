/**
 * Accessible loading indicator.
 */
export function LoadingSpinner(): React.ReactElement {
  return (
    <div className="loading-spinner" role="status" aria-label="Loading">
      <div className="loading-spinner__ring" aria-hidden="true" />
    </div>
  )
}

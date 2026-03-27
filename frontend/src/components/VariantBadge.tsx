import type { AutosarVariant } from '../api/schema'

type Props = {
  variant: AutosarVariant
}

/**
 * Small inline badge indicating Classic or Adaptive AUTOSAR variant.
 */
export function VariantBadge({ variant }: Props): React.ReactElement {
  return (
    <span className={`variant-badge variant-badge--${variant}`}>
      {variant === 'classic' ? 'Classic' : 'Adaptive'}
    </span>
  )
}

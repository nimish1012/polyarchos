import { NavLink } from 'react-router-dom'

const LINKS = [
  { to: '/components', label: 'Components' },
  { to: '/graph', label: 'Graph' },
  { to: '/search', label: 'Search' },
  { to: '/validate', label: 'ARXML Validator' },
  { to: '/playground', label: 'API Playground' },
] as const

/**
 * Top-level navigation bar.
 */
export function NavBar(): React.ReactElement {
  return (
    <nav className="navbar" aria-label="Main navigation">
      <span className="navbar__brand">polyarchos</span>
      <ul className="navbar__links" role="list">
        {LINKS.map(({ to, label }) => (
          <li key={to}>
            <NavLink
              to={to}
              className={({ isActive }) =>
                `navbar__link${isActive ? ' navbar__link--active' : ''}`
              }
            >
              {label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}

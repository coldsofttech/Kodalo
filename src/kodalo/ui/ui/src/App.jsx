import { useState } from 'react';
import AboutPage from './pages/About.jsx';
import HomePage from './pages/Home.jsx';
import BrandsPage from './pages/brands/Brands.jsx';
import CanvasesPage from './pages/brands/Canvases.jsx';
import LayoutsPage from './pages/brands/Layouts.jsx';
import PalettesPage from './pages/brands/Palettes.jsx';
import RepositoriesPage from './pages/repositories/Repositories.jsx';
import StudioPage from './pages/studio/Studio.jsx';
import SettingsPage from './pages/settings/Settings.jsx';

/** Brands, Palettes, Canvases and Layouts sit in a collapsible Brands menu. */
const BRANDS_MENU = 'brands-menu';
const PAGES = [
  ['home', 'Home', []],
  ['studio', 'Studio', []],
  ['repositories', 'Repositories', []],
  [
    BRANDS_MENU,
    'Brands',
    [
      ['brands', 'Brands'],
      ['palettes', 'Palettes'],
      ['canvases', 'Canvases'],
      ['layouts', 'Layouts'],
    ],
  ],
  ['settings', 'Settings', []],
  ['about', 'About', []],
];

const BRANDS_PAGES = ['brands', 'palettes', 'canvases', 'layouts'];

/** @param {{ page: string, pageKey: string, label: string, onOpen: (key: string) => void }} props */
function NavButton({ page, pageKey, label, onOpen }) {
  return (
    <button
      type="button"
      aria-current={page === pageKey ? 'page' : undefined}
      onClick={() => onOpen(pageKey)}
    >
      {label}
    </button>
  );
}

export default function App() {
  const [page, setPage] = useState('home');
  /** Pages opened so far. A page is mounted on its first visit, so start-up makes no API calls. */
  const [visited, setVisited] = useState(() => new Set(['home']));
  /** @param {string} key */
  const open = (key) => {
    setVisited((seen) => (seen.has(key) ? seen : new Set(seen).add(key)));
    setPage(key);
    if (BRANDS_PAGES.includes(key)) setBrandsOpen(true);
  };
  /** The Brands menu starts collapsed. */
  const [brandsOpen, setBrandsOpen] = useState(false);
  /** Counts changes to canvases, palettes and layouts, so the brand editor reloads its lists. */
  const [catalogRevision, setCatalogRevision] = useState(0);
  const changed = () => setCatalogRevision((n) => n + 1);
  return (
    <div className="shell">
      <nav className="nav" aria-label="Main">
        <p className="nav-title">Kodalo</p>
        <ul>
          {PAGES.map(([key, label, children]) => (
            <li key={key}>
              {children.length > 0 ? (
                <button
                  type="button"
                  aria-expanded={brandsOpen}
                  onClick={() => setBrandsOpen((isOpen) => !isOpen)}
                >
                  {label}
                </button>
              ) : (
                <NavButton page={page} pageKey={key} label={label} onOpen={open} />
              )}
              {children.length > 0 && brandsOpen ? (
                <ul className="subnav" aria-label={`${label} sections`}>
                  {children.map(([childKey, childLabel]) => (
                    <li key={childKey}>
                      <NavButton page={page} pageKey={childKey} label={childLabel} onOpen={open} />
                    </li>
                  ))}
                </ul>
              ) : null}
            </li>
          ))}
        </ul>
      </nav>
      <main className="content">
        {/* Once opened, a page stays mounted, so switching never loses unsaved edits. */}
        {[
          ['home', <HomePage key="home" onOpen={open} />],
          [
            'brands',
            <BrandsPage key="brands" catalogRevision={catalogRevision} onCatalogChange={changed} />,
          ],
          [
            'canvases',
            <CanvasesPage key="canvases" onChange={changed} revision={catalogRevision} />,
          ],
          [
            'palettes',
            <PalettesPage key="palettes" onChange={changed} revision={catalogRevision} />,
          ],
          ['layouts', <LayoutsPage key="layouts" onChange={changed} revision={catalogRevision} />],
          [
            'studio',
            <StudioPage
              key="studio"
              visible={page === 'studio'}
              onOpenRepositories={() => open('repositories')}
            />,
          ],
          [
            'repositories',
            <RepositoriesPage
              key="repositories"
              visible={page === 'repositories'}
              onOpenSettings={() => open('settings')}
            />,
          ],
          ['settings', <SettingsPage key="settings" />],
          ['about', <AboutPage key="about" />],
        ].map(([key, element]) =>
          visited.has(String(key)) ? (
            <div key={String(key)} hidden={page !== key}>
              {element}
            </div>
          ) : null,
        )}
      </main>
    </div>
  );
}

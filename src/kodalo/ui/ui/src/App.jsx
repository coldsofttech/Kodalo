import { useState } from 'react';
import AboutPage from './pages/About.jsx';
import HomePage from './pages/Home.jsx';
import BrandsPage from './pages/brands/Brands.jsx';
import CanvasesPage from './pages/brands/Canvases.jsx';
import LayoutsPage from './pages/brands/Layouts.jsx';
import PalettesPage from './pages/brands/Palettes.jsx';
import StudioPage from './pages/Studio.jsx';
import SettingsPage from './pages/Settings.jsx';

/** Canvases, Palettes and Layouts are sub-menus of Brands. */
const PAGES = [
  ['home', 'Home', []],
  [
    'brands',
    'Brands',
    [
      ['canvases', 'Canvases'],
      ['palettes', 'Palettes'],
      ['layouts', 'Layouts'],
    ],
  ],
  ['studio', 'Studio', []],
  ['settings', 'Settings', []],
  ['about', 'About', []],
];

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
  };
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
              <NavButton page={page} pageKey={key} label={label} onOpen={open} />
              {children.length > 0 ? (
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

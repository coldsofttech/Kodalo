import { useCallback, useRef, useState } from 'react';
import AboutPage from './pages/About.jsx';
import HomePage from './pages/Home.jsx';
import BrandsPage from './pages/brands/Brands.jsx';
import CanvasesPage from './pages/brands/Canvases.jsx';
import LayoutsPage from './pages/brands/Layouts.jsx';
import PalettesPage from './pages/brands/Palettes.jsx';
import RepositoriesPage from './pages/repositories/Repositories.jsx';
import StudioPage from './pages/studio/Studio.jsx';
import SettingsPage from './pages/settings/Settings.jsx';
import { Button } from './components/controls.jsx';
import { UnsavedContext } from './libs/unsaved.js';

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
  /** The parts of the open page that hold unsaved edits (see `useUnsavedGuard`). */
  const unsaved = useRef(/** @type {Set<string>} */ (new Set()));
  /** The page waiting for a yes or no because the open one holds unsaved edits. */
  const [pending, setPending] = useState(/** @type {string | null} */ (null));
  const report = useCallback(
    /** @param {string} id @param {boolean} dirty */
    (id, dirty) => {
      if (dirty) unsaved.current.add(id);
      else unsaved.current.delete(id);
    },
    [],
  );
  /** @param {string} key */
  const go = (key) => {
    unsaved.current.clear();
    setPending(null);
    setPage(key);
    if (BRANDS_PAGES.includes(key)) setBrandsOpen(true);
  };
  /** Only the open page is mounted, so every visit starts fresh. @param {string} key */
  const open = (key) => {
    if (key === page) return;
    if (unsaved.current.size > 0) setPending(key);
    else go(key);
  };
  const pendingLabel = [...PAGES, ...PAGES.flatMap(([, , children]) => children)].find(
    ([key]) => key === pending,
  )?.[1];
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
        {pending ? (
          <div className="ask" role="alertdialog" aria-label="Unsaved changes">
            <p>You have unsaved changes. Discard them and open {pendingLabel}?</p>
            <Button appearance="accent" onClick={() => go(pending)}>
              Discard changes
            </Button>
            <Button appearance="outline" onClick={() => setPending(null)}>
              Keep editing
            </Button>
          </div>
        ) : null}
        {/* Only the open page is mounted: leaving it drops its state, so coming back starts from
            scratch. A page with unsaved edits asks first (see `useUnsavedGuard`). */}
        <UnsavedContext.Provider value={report}>
          {[
            ['home', <HomePage key="home" onOpen={open} />],
            [
              'brands',
              <BrandsPage
                key="brands"
                catalogRevision={catalogRevision}
                onCatalogChange={changed}
              />,
            ],
            [
              'canvases',
              <CanvasesPage key="canvases" onChange={changed} revision={catalogRevision} />,
            ],
            [
              'palettes',
              <PalettesPage key="palettes" onChange={changed} revision={catalogRevision} />,
            ],
            [
              'layouts',
              <LayoutsPage key="layouts" onChange={changed} revision={catalogRevision} />,
            ],
            [
              'studio',
              <StudioPage key="studio" visible onOpenRepositories={() => open('repositories')} />,
            ],
            [
              'repositories',
              <RepositoriesPage
                key="repositories"
                visible
                onOpenSettings={() => open('settings')}
              />,
            ],
            ['settings', <SettingsPage key="settings" />],
            ['about', <AboutPage key="about" />],
          ].map(([key, element]) => (key === page ? <div key={String(key)}>{element}</div> : null))}
        </UnsavedContext.Provider>
      </main>
    </div>
  );
}

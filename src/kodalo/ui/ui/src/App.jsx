import { useState } from 'react';
import AboutPage from './pages/About.jsx';
import BrandsPage from './pages/brands/Brands.jsx';
import CanvasesPage from './pages/brands/Canvases.jsx';
import LayoutsPage from './pages/brands/Layouts.jsx';
import PalettesPage from './pages/brands/Palettes.jsx';
import StudioPage from './pages/Studio.jsx';
import SettingsPage from './pages/Settings.jsx';

/** Canvases, Palettes and Layouts are sub-menus of Brands. */
const PAGES = [
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
  const [page, setPage] = useState('brands');
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
              <NavButton page={page} pageKey={key} label={label} onOpen={setPage} />
              {children.length > 0 ? (
                <ul className="subnav" aria-label={`${label} sections`}>
                  {children.map(([childKey, childLabel]) => (
                    <li key={childKey}>
                      <NavButton
                        page={page}
                        pageKey={childKey}
                        label={childLabel}
                        onOpen={setPage}
                      />
                    </li>
                  ))}
                </ul>
              ) : null}
            </li>
          ))}
        </ul>
      </nav>
      <main className="content">
        {/* All pages stay mounted, so switching never loses unsaved edits. */}
        <div hidden={page !== 'brands'}>
          <BrandsPage catalogRevision={catalogRevision} onCatalogChange={changed} />
        </div>
        <div hidden={page !== 'canvases'}>
          <CanvasesPage onChange={changed} revision={catalogRevision} />
        </div>
        <div hidden={page !== 'palettes'}>
          <PalettesPage onChange={changed} revision={catalogRevision} />
        </div>
        <div hidden={page !== 'layouts'}>
          <LayoutsPage onChange={changed} revision={catalogRevision} />
        </div>
        <div hidden={page !== 'studio'}>
          <StudioPage visible={page === 'studio'} onOpenSettings={() => setPage('settings')} />
        </div>
        <div hidden={page !== 'settings'}>
          <SettingsPage />
        </div>
        <div hidden={page !== 'about'}>
          <AboutPage />
        </div>
      </main>
    </div>
  );
}

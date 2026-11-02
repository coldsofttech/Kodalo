import { useState } from 'react';
import AboutPage from './pages/About.jsx';
import BrandsPage from './pages/Brands.jsx';
import SettingsPage from './pages/Settings.jsx';

const PAGES = [
  ['brands', 'Brands'],
  ['settings', 'Settings'],
  ['about', 'About'],
];

export default function App() {
  const [page, setPage] = useState('brands');
  return (
    <div className="shell">
      <nav className="nav" aria-label="Main">
        <p className="nav-title">Kodalo</p>
        <ul>
          {PAGES.map(([key, label]) => (
            <li key={key}>
              <button
                type="button"
                aria-current={page === key ? 'page' : undefined}
                onClick={() => setPage(key)}
              >
                {label}
              </button>
            </li>
          ))}
        </ul>
      </nav>
      <main className="content">
        {/* All pages stay mounted, so switching never loses unsaved edits. */}
        <div hidden={page !== 'brands'}>
          <BrandsPage />
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

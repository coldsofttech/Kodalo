import { useState } from 'react';
import AboutPage from './pages/About.jsx';
import BrandsPage from './pages/Brands.jsx';

const PAGES = [
  ['brands', 'Brands'],
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
        {/* Both pages stay mounted, so switching never loses unsaved edits. */}
        <div hidden={page !== 'brands'}>
          <BrandsPage />
        </div>
        <div hidden={page !== 'about'}>
          <AboutPage />
        </div>
      </main>
    </div>
  );
}

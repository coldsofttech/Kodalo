import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './libs/fluent.js';
import App from './App.jsx';
import { loadTheme } from './libs/theme.js';
import './styles/fonts.css';
import './styles/app.css';
import './styles/preview.css';

loadTheme();

const root = document.getElementById('root');
if (root) {
  createRoot(root).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}

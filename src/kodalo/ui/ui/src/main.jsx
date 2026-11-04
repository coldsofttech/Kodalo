import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './fluent.js';
import App from './App.jsx';
import { loadTheme } from './theme.js';
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

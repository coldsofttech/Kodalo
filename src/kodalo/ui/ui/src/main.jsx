import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './fluent.js';
import App from './App.jsx';
import './styles/fonts.css';
import './styles/app.css';
import './styles/preview.css';

const root = document.getElementById('root');
if (root) {
  createRoot(root).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}

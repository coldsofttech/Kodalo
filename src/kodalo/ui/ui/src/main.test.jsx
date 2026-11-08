import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';

const started = vi.hoisted(() => ({ loadTheme: vi.fn(), fluent: vi.fn() }));

vi.mock('./libs/fluent.js', () => {
  started.fluent();
  return {};
});
vi.mock('./libs/theme.js', () => ({ loadTheme: started.loadTheme }));
vi.mock('./App.jsx', () => ({ default: () => <p>The app</p> }));
vi.mock('./styles/fonts.css', () => ({}));
vi.mock('./styles/app.css', () => ({}));
vi.mock('./styles/preview.css', () => ({}));

beforeEach(() => {
  vi.resetModules();
  started.loadTheme.mockClear();
  started.fluent.mockClear();
});

afterEach(() => {
  document.body.innerHTML = '';
});

describe('main', () => {
  it('registers Fluent, loads the theme and shows the app in the page', async () => {
    document.body.innerHTML = '<div id="root"></div>';

    await import('./main.jsx');

    expect(started.fluent).toHaveBeenCalledTimes(1);
    expect(started.loadTheme).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(screen.getByText('The app')).toBeInTheDocument());
  });

  it('does nothing more when the page has no root', async () => {
    await import('./main.jsx');

    expect(started.loadTheme).toHaveBeenCalledTimes(1);
    expect(screen.queryByText('The app')).not.toBeInTheDocument();
  });
});

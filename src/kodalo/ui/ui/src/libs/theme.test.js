import { afterEach, describe, expect, it, vi } from 'vitest';
import { mockApi } from '../testing.js';
import { loadTheme, onThemeChange, setTheme, THEMES } from './theme.js';

afterEach(() => {
  vi.unstubAllGlobals();
  setTheme('system');
});

describe('theme', () => {
  it('offers system, light and dark', () => {
    expect(THEMES).toEqual(['system', 'light', 'dark']);
  });

  it('sets the theme on the page and tells the listeners', () => {
    const seen = /** @type {string[]} */ ([]);
    const stop = onThemeChange((theme) => seen.push(theme));

    setTheme('dark');

    expect(document.documentElement.dataset.theme).toBe('dark');
    expect(seen.slice(-1)).toEqual(['dark']);
    stop();
  });

  it('runs a new listener at once with the current theme', () => {
    setTheme('light');
    const seen = /** @type {string[]} */ ([]);

    const stop = onThemeChange((theme) => seen.push(theme));

    expect(seen).toEqual(['light']);
    stop();
  });

  it('stops telling a listener that unsubscribed', () => {
    const seen = /** @type {string[]} */ ([]);
    const stop = onThemeChange((theme) => seen.push(theme));
    stop();

    setTheme('dark');

    expect(seen).toEqual(['system']);
  });

  it('follows the system for a theme it does not know', () => {
    setTheme('purple');

    expect(document.documentElement.dataset.theme).toBe('system');
  });

  it('applies the saved theme at launch', async () => {
    mockApi((method, path) => (path === '/api/v1/settings/theme' ? { theme: 'dark' } : undefined));

    await loadTheme();

    expect(document.documentElement.dataset.theme).toBe('dark');
  });

  it('follows the system when the saved theme cannot be read', async () => {
    setTheme('dark');
    mockApi(() => [500, { detail: 'broken' }]);

    await loadTheme();

    expect(document.documentElement.dataset.theme).toBe('system');
  });
});

// The window's theme: "light", "dark", or "system" to follow the operating system.
// The page styles read `data-theme` on <html>; fluent.js listens here for the Fluent components.
import { getTheme } from './api.js';

export const THEMES = ['system', 'light', 'dark'];

/** @type {Set<(theme: string) => void>} */
const listeners = new Set();

/** @param {string} theme */
export function setTheme(theme) {
  const value = THEMES.includes(theme) ? theme : 'system';
  document.documentElement.dataset.theme = value;
  for (const listener of listeners) listener(value);
}

/**
 * Run `listener` now and whenever the theme changes.
 * @param {(theme: string) => void} listener
 */
export function onThemeChange(listener) {
  listeners.add(listener);
  listener(document.documentElement.dataset.theme ?? 'system');
  return () => listeners.delete(listener);
}

/** Apply the saved theme at launch. If it cannot be read, the window follows the system. */
export async function loadTheme() {
  try {
    setTheme((await getTheme()).theme);
  } catch {
    setTheme('system');
  }
}

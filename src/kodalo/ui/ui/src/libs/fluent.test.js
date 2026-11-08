import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const fluent = vi.hoisted(() => ({
  register: vi.fn(),
  setValueFor: vi.fn(),
  element: vi.fn((name) => name),
}));

vi.mock('@fluentui/web-components', () => ({
  baseLayerLuminance: { setValueFor: fluent.setValueFor },
  fluentButton: () => fluent.element('button'),
  fluentNumberField: () => fluent.element('number-field'),
  fluentSwitch: () => fluent.element('switch'),
  fluentTextArea: () => fluent.element('text-area'),
  fluentTextField: () => fluent.element('text-field'),
  provideFluentDesignSystem: () => ({ register: fluent.register }),
  StandardLuminance: { DarkMode: 0.2, LightMode: 0.98 },
}));

/** @type {{ matches: boolean, change: (() => void) | null }} */
const system = { matches: false, change: null };

beforeEach(() => {
  vi.resetModules();
  fluent.register.mockClear();
  fluent.setValueFor.mockClear();
  system.matches = false;
  system.change = null;
  vi.stubGlobal(
    'matchMedia',
    vi.fn(() => ({
      get matches() {
        return system.matches;
      },
      addEventListener: (/** @type {string} */ _, /** @type {() => void} */ listener) => {
        system.change = listener;
      },
    })),
  );
});

afterEach(() => vi.unstubAllGlobals());

/** Load fluent.js and the theme module it listens to, both fresh. */
async function load() {
  await import('./fluent.js');
  return import('./theme.js');
}

describe('fluent', () => {
  it('registers the elements the app uses', async () => {
    await load();

    expect(fluent.register).toHaveBeenCalledWith(
      'button',
      'number-field',
      'switch',
      'text-area',
      'text-field',
    );
  });

  it('follows the system while the theme is system', async () => {
    await load();
    expect(fluent.setValueFor).toHaveBeenLastCalledWith(document.body, 0.98);

    system.matches = true;
    system.change?.();

    expect(fluent.setValueFor).toHaveBeenLastCalledWith(document.body, 0.2);
  });

  it('uses the chosen theme whatever the system does', async () => {
    const { setTheme } = await load();
    system.matches = true;

    setTheme('light');
    expect(fluent.setValueFor).toHaveBeenLastCalledWith(document.body, 0.98);

    system.matches = false;
    setTheme('dark');
    expect(fluent.setValueFor).toHaveBeenLastCalledWith(document.body, 0.2);
  });
});

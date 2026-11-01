// Helpers for the tests: a fake Python side, sample brands, and a way to "type" into the Fluent
// custom elements (which keep their value as a property and report it with DOM events).
import { fireEvent } from '@testing-library/react';
import { vi } from 'vitest';

const pair = (/** @type {string} */ light, /** @type {string} */ dark) => ({ light, dark });
const font = (/** @type {string} */ family) => ({ family, source: 'bundled' });

export const SAMPLE_DATA = () => ({
  schema_version: 1,
  colors: {
    background: pair('#ffffff', '#0b1020'),
    primary: pair('#2563eb', '#60a5fa'),
    secondary: pair('#7c3aed', '#a78bfa'),
    text: pair('#111827', '#f3f4f6'),
    background_alt: pair('#f1f5f9', '#151b30'),
    primary_alt: pair('#1d4ed8', '#93c5fd'),
    secondary_alt: pair('#6d28d9', '#c4b5fd'),
    text_alt: pair('#0f172a', '#e5e7eb'),
  },
  fonts: {
    heading: font('Poppins'),
    heading_alt: font('Space Grotesk'),
    body: font('Inter'),
    body_alt: font('Source Sans 3'),
    mono: font('JetBrains Mono'),
    mono_alt: font('Fira Code'),
  },
  logo: {
    file: null,
    dark_file: null,
    position: 'top_left',
    size_percent: 14,
    padding: 48,
    show_on: 'all',
  },
  layout: {
    canvas: { preset: 'instagram_portrait', width: 1080, height: 1350 },
    margin_top: 96,
    margin_side: 80,
    margin_bottom: 96,
    corner_radius: 24,
    slide_numbers: true,
    footer_text: '',
    align: 'left',
    density: 'regular',
  },
});

export const makeBrand = (
  /** @type {string} */ id,
  /** @type {string} */ name,
  /** @type {boolean} */ isDefault = false,
) => ({
  id,
  name,
  is_default: isDefault,
  data: SAMPLE_DATA(),
  created_at: '2026-11-01T09:00:00+00:00',
  updated_at: '2026-11-01T09:00:00+00:00',
});

export const PALETTES = [
  { key: 'midnight', title: 'Midnight', data: SAMPLE_DATA() },
  { key: 'paper', title: 'Paper', data: SAMPLE_DATA() },
];
export const FONTS = [
  { family: 'Inter', category: 'sans', source: 'bundled' },
  { family: 'Poppins', category: 'sans', source: 'bundled' },
  { family: 'Lora', category: 'serif', source: 'bundled' },
  { family: 'Segoe UI', category: 'sans', source: 'system' },
];
export const PRESETS = [
  { key: 'instagram_portrait', width: 1080, height: 1350 },
  { key: 'instagram_square', width: 1080, height: 1080 },
];
export const NO_FAILURES = Array.from({ length: 12 }, () => ({
  color: 'text',
  on: 'background',
  mode: 'light',
  ratio: 12,
  minimum: 4.5,
  passes: true,
}));

/**
 * Fake the Python side. `handler(method, path, body)` returns the JSON to send, `[status, json]`,
 * or undefined for "no such route". Every call is recorded in the returned `calls` list.
 * @param {(method: string, path: string, body: any) => unknown} handler
 */
export function mockApi(handler) {
  /** @type {{ method: string, path: string, body: any }[]} */
  const calls = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (/** @type {string} */ path, /** @type {RequestInit} */ options = {}) => {
      const method = options.method ?? 'GET';
      const body = typeof options.body === 'string' ? JSON.parse(options.body) : options.body;
      calls.push({ method, path, body });
      const result = handler(method, path, body);
      if (result === undefined) {
        return { ok: false, status: 404, json: async () => ({ detail: `${method} ${path}` }) };
      }
      const [status, json] =
        Array.isArray(result) && typeof result[0] === 'number' ? result : [200, result];
      if (status === 204) return { ok: true, status, json: async () => null };
      return { ok: status < 400, status, json: async () => json };
    }),
  );
  return calls;
}

/** Type into a Fluent text or number field, the way its own events report it. */
export function typeInto(/** @type {HTMLElement} */ element, /** @type {string} */ text) {
  Object.assign(element, { value: text });
  fireEvent.input(element);
}

/** Flip a Fluent switch. */
export function setChecked(/** @type {HTMLElement} */ element, /** @type {boolean} */ checked) {
  Object.assign(element, { checked });
  fireEvent.change(element);
}

export const DOCTOR = {
  healthy: true,
  checks: [
    { name: 'Kodalo', ok: true, detail: '0.1.0', required: false },
    { name: 'Python', ok: true, detail: '3.11.9 (requires 3.11+)', required: true },
    { name: 'Fonts', ok: false, detail: 'none installed', required: false },
  ],
};

/**
 * A small in-memory stand-in for the whole API. `state.brands` is what the "database" holds.
 * @param {ReturnType<typeof makeBrand>[]} initial
 */
export function createBackend(initial = []) {
  const state = {
    brands: initial,
    contrast: /** @type {any[]} */ (NO_FAILURES),
    doctor: /** @type {any} */ (DOCTOR),
    counter: 0,
    now: 0,
  };
  const find = (/** @type {string} */ id) => state.brands.find((brand) => brand.id === id);
  const touch = (/** @type {any} */ brand) => {
    state.now += 1;
    brand.updated_at = `2026-11-01T10:00:${String(state.now).padStart(2, '0')}+00:00`;
    return brand;
  };
  /** @type {(method: string, path: string, body: any) => unknown} */
  const handler = (method, path, body) => {
    const url = new URL(path, 'http://app');
    const parts = url.pathname.replace('/api/v1/', '').split('/');
    if (url.pathname === '/api/bridge/app_info') {
      return { available: true, result: { name: 'Kodalo', version: '1.2.3' } };
    }
    if (parts[0] === 'palettes') return PALETTES;
    if (parts[0] === 'fonts') return FONTS;
    if (parts[0] === 'canvas-presets') return PRESETS;
    if (parts[0] === 'doctor') return state.doctor;
    if (parts[0] !== 'brands') return undefined;
    if (parts.length === 1) {
      if (method === 'GET') return state.brands;
      state.counter += 1;
      const brand = makeBrand(`new-${state.counter}`, body.name, state.brands.length === 0);
      if (state.brands.some((item) => item.name.toLowerCase() === body.name.toLowerCase())) {
        return [409, { detail: `A brand named "${body.name}" already exists.` }];
      }
      state.brands = [...state.brands, brand];
      return [201, brand];
    }
    if (parts[1] === 'contrast') return state.contrast;
    if (parts[1] === 'import') {
      state.counter += 1;
      const brand = makeBrand(`new-${state.counter}`, url.searchParams.get('name') ?? body.name);
      state.brands = [...state.brands, brand];
      return [201, brand];
    }
    const brand = find(parts[1]);
    if (!brand) return [404, { detail: 'That brand does not exist.' }];
    const action = parts[2];
    if (action === undefined) {
      if (method === 'DELETE') {
        state.brands = state.brands.filter((item) => item.id !== brand.id);
        if (brand.is_default && state.brands[0]) state.brands[0].is_default = true;
        return [204, null];
      }
      if (
        body.name !== undefined &&
        state.brands.some((b) => b.id !== brand.id && b.name === body.name)
      ) {
        return [409, { detail: `A brand named "${body.name}" already exists.` }];
      }
      Object.assign(brand, body);
      return touch(brand);
    }
    if (action === 'default') {
      for (const item of state.brands) item.is_default = item.id === brand.id;
      return touch(brand);
    }
    if (action === 'duplicate') {
      state.counter += 1;
      const copy = makeBrand(`new-${state.counter}`, body.name);
      state.brands = [...state.brands, copy];
      return [201, copy];
    }
    if (action === 'export') {
      return { format: 'kodalo-brand', version: 1, name: brand.name, data: brand.data, logos: {} };
    }
    if (action === 'logo') {
      const dark = url.searchParams.get('variant') === 'dark';
      const key = dark ? 'dark_file' : 'file';
      brand.data.logo[key] = method === 'PUT' ? `${'a'.repeat(32)}.png` : null;
      return touch(brand);
    }
    return undefined;
  };
  return { state, handler };
}

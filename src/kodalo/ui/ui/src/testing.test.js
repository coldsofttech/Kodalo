import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  CANVASES,
  createBackend,
  makeBrand,
  makeRepo,
  mockApi,
  PALETTES,
  setChecked,
  typeInto,
} from './testing.js';

afterEach(() => vi.unstubAllGlobals());

/** Call the fake API the way the app does. */
async function call(/** @type {string} */ path, /** @type {RequestInit} */ options = {}) {
  const response = await fetch(path, options);
  return { status: response.status, ok: response.ok, body: await response.json() };
}

describe('mockApi', () => {
  it('records every call, with the body parsed', async () => {
    const calls = mockApi(() => ({}));

    await call('/a');
    await call('/b', { method: 'POST', body: '{"x":1}' });

    expect(calls).toEqual([
      { method: 'GET', path: '/a', body: undefined },
      { method: 'POST', path: '/b', body: { x: 1 } },
    ]);
  });

  it('answers 200 with the value the handler returned', async () => {
    mockApi(() => ({ hello: 'world' }));

    expect(await call('/a')).toEqual({ status: 200, ok: true, body: { hello: 'world' } });
  });

  it('answers with the status the handler chose', async () => {
    mockApi(() => [409, { detail: 'Taken.' }]);

    expect(await call('/a')).toEqual({ status: 409, ok: false, body: { detail: 'Taken.' } });
  });

  it('answers 204 with no content', async () => {
    mockApi(() => [204, null]);

    expect(await call('/a')).toEqual({ status: 204, ok: true, body: null });
  });

  it('answers 404 for a route the handler does not know', async () => {
    mockApi(() => undefined);

    expect(await call('/missing', { method: 'DELETE' })).toEqual({
      status: 404,
      ok: false,
      body: { detail: 'DELETE /missing' },
    });
  });
});

describe('form helpers', () => {
  it('types into a field the way Fluent reports it', () => {
    const field = document.createElement('input');
    const seen = vi.fn(() => field.value);
    field.addEventListener('input', seen);

    typeInto(field, 'Acme');

    expect(seen).toHaveReturnedWith('Acme');
  });

  it('flips a switch and reports the change', () => {
    const element = document.createElement('div');
    const seen = vi.fn(() => /** @type {any} */ (element).checked);
    element.addEventListener('change', seen);

    setChecked(element, true);

    expect(seen).toHaveReturnedWith(true);
  });
});

describe('sample data', () => {
  it('makes a repository and a brand with the ids it is given', () => {
    expect(makeRepo('octo').owner).toBe('octo');
    expect(makeBrand('b1', 'Acme', true)).toMatchObject({
      id: 'b1',
      name: 'Acme',
      is_default: true,
    });
  });

  it('offers system canvases and palettes', () => {
    expect(CANVASES.length).toBeGreaterThan(0);
    expect(PALETTES.map((palette) => palette.id)).toContain('system-midnight');
  });
});

describe('createBackend', () => {
  it('lists, creates and deletes brands in memory', async () => {
    const backend = createBackend([makeBrand('b1', 'Acme', true)]);
    mockApi(backend.handler);

    const created = await call('/api/v1/brands', {
      method: 'POST',
      body: JSON.stringify({ name: 'Beta' }),
    });
    const listed = await call('/api/v1/brands');
    await call('/api/v1/brands/b1', { method: 'DELETE' });

    expect(created.status).toBe(201);
    expect(listed.body.map((/** @type {any} */ brand) => brand.name)).toEqual(['Acme', 'Beta']);
    expect(backend.state.brands.map((brand) => brand.name)).toEqual(['Beta']);
  });

  it('refuses a brand name that is already taken, whatever its case', async () => {
    mockApi(createBackend([makeBrand('b1', 'Acme', true)]).handler);

    const again = await call('/api/v1/brands', {
      method: 'POST',
      body: JSON.stringify({ name: 'ACME' }),
    });

    expect(again.status).toBe(409);
  });

  it('answers the other pages of the app', async () => {
    mockApi(createBackend([]).handler);

    expect((await call('/api/v1/doctor')).body.healthy).toBe(true);
    expect((await call('/api/v1/settings/github')).body.mode).toBe('gh_cli');
    expect((await call('/api/v1/nothing')).status).toBe(404);
  });
});

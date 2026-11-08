import { afterEach, describe, expect, it, vi } from 'vitest';
import { mockApi } from '../testing.js';
import {
  ApiError,
  appInfo,
  chooseFolder,
  createBrand,
  deleteBrand,
  importBrand,
  listBrands,
  logoUrl,
  openExternal,
  saveJsonFile,
  updateBrand,
  uploadLogo,
} from './api.js';

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('requests', () => {
  it('reads JSON from a relative path', async () => {
    const calls = mockApi(() => [{ id: 'a' }]);

    expect(await listBrands()).toEqual([{ id: 'a' }]);

    expect(calls).toEqual([{ method: 'GET', path: '/api/v1/brands', body: undefined }]);
  });

  it('sends a JSON body with its content type', async () => {
    mockApi(() => ({ id: 'a' }));

    await createBrand({ name: 'Acme' });

    const [path, options] = vi.mocked(fetch).mock.calls[0];
    expect(path).toBe('/api/v1/brands');
    expect(options).toMatchObject({
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{"name":"Acme"}',
    });
  });

  it('uses the right verb and address for a change', async () => {
    const calls = mockApi(() => ({}));

    await updateBrand('b1', { name: 'New' });
    await deleteBrand('b1');

    expect(calls.map((call) => `${call.method} ${call.path}`)).toEqual([
      'PATCH /api/v1/brands/b1',
      'DELETE /api/v1/brands/b1',
    ]);
  });

  it('gives nothing back for an empty answer', async () => {
    mockApi(() => [204, null]);

    expect(await deleteBrand('b1')).toBeNull();
  });

  it('names the import in the address only when it is given', async () => {
    const calls = mockApi(() => ({}));

    await importBrand({ format: 'x' });
    await importBrand({ format: 'x' }, 'My brand & more');

    expect(calls.map((call) => call.path)).toEqual([
      '/api/v1/brands/import',
      '/api/v1/brands/import?name=My%20brand%20%26%20more',
    ]);
  });

  it('uploads a logo as it is, with its own type', async () => {
    mockApi(() => ({}));
    const file = new File(['<svg/>'], 'logo.svg', { type: 'image/svg+xml' });

    await uploadLogo('b1', file, 'dark');

    const [path, options] = vi.mocked(fetch).mock.calls[0];
    expect(path).toBe('/api/v1/brands/b1/logo?variant=dark');
    expect(options).toMatchObject({
      method: 'PUT',
      headers: { 'Content-Type': 'image/svg+xml' },
      body: file,
    });
  });

  it('builds the address of a logo that changes with its version', () => {
    expect(logoUrl('b1', 'light', '2026-11-01T09:00:00+00:00')).toBe(
      '/api/v1/brands/b1/logo?variant=light&v=2026-11-01T09%3A00%3A00%2B00%3A00',
    );
  });
});

describe('failures', () => {
  it('shows the detail the server gave', async () => {
    mockApi(() => [404, { detail: 'No such brand.' }]);

    const failure = await listBrands().catch((error) => error);

    expect(failure).toBeInstanceOf(ApiError);
    expect(failure).toMatchObject({ message: 'No such brand.', status: 404, name: 'ApiError' });
  });

  it('shows the first validation error with the field it is about', async () => {
    mockApi(() => [
      422,
      { errors: [{ loc: ['body', 'data', 'name'], msg: 'Too long.' }], detail: 'Invalid.' },
    ]);

    await expect(createBrand({ name: 'x' })).rejects.toThrow('data.name: Too long.');
  });

  it('shows a validation error that is not about a field', async () => {
    mockApi(() => [422, { errors: [{ msg: 'Bad input.' }] }]);

    await expect(createBrand({ name: 'x' })).rejects.toThrow('Bad input.');
  });

  it('says what went wrong without leaking anything when there is no detail', async () => {
    mockApi(() => [500, { trace: 'secret' }]);

    await expect(listBrands()).rejects.toThrow('Something went wrong (500).');
  });

  it('says Kodalo could not be reached when the call does not get through', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('failed')));

    const failure = await listBrands().catch((error) => error);

    expect(failure).toMatchObject({ message: 'Kodalo could not be reached.', status: 0 });
  });
});

describe('the window bridge', () => {
  it('returns the app name and version', async () => {
    mockApi(() => ({ available: true, result: { name: 'Kodalo', version: '0.1.0' } }));

    expect(await appInfo()).toEqual({ name: 'Kodalo', version: '0.1.0' });
  });

  it('says why the app info is not available', async () => {
    mockApi(() => ({ available: false, reason: 'No window' }));

    await expect(appInfo()).rejects.toThrow('No window');
  });

  it('asks for a folder, and gives an empty text when the dialog is cancelled', async () => {
    mockApi(() => ({ available: true, result: 'C:/Posts' }));
    expect(await chooseFolder()).toBe('C:/Posts');

    mockApi(() => ({ available: true, result: null }));
    expect(await chooseFolder()).toBe('');
  });

  it('needs the window to choose a folder', async () => {
    mockApi(() => ({ available: false }));

    await expect(chooseFolder()).rejects.toThrow('Choosing a folder needs the Kodalo window.');
  });

  it('saves a file in three steps and reports what happened', async () => {
    const calls = mockApi((method, path) =>
      path.endsWith('save_file')
        ? { available: true, result: 'C:/a.json' }
        : { available: true, result: true },
    );

    expect(await saveJsonFile('a.json', '{}')).toBe('saved');
    expect(calls[0].body).toEqual({ filename: 'a.json', file_types: ['JSON files (*.json)'] });
    expect(calls[1].body).toEqual({ path: 'C:/a.json', text: '{}' });

    mockApi(() => ({ available: true, result: null }));
    expect(await saveJsonFile('a.json', '{}')).toBe('cancelled');

    mockApi(() => ({ available: false }));
    expect(await saveJsonFile('a.json', '{}')).toBe('unavailable');
  });

  it('opens an address in the system browser, or in a new tab outside the window', async () => {
    const open = vi.fn();
    vi.stubGlobal('open', open);
    mockApi(() => ({ available: true }));
    await openExternal('https://example.com');
    expect(open).not.toHaveBeenCalled();

    mockApi(() => ({ available: false }));
    await openExternal('https://example.com');
    expect(open).toHaveBeenCalledWith('https://example.com', '_blank', 'noopener');
  });
});

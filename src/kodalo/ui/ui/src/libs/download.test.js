import { afterEach, describe, expect, it, vi } from 'vitest';
import { mockApi } from '../testing.js';
import { fileNameFor, readJson, saveJson, saveText } from './download.js';

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

const TEXT = { mime: 'text/plain', label: 'Text files (*.txt)' };

/**
 * A window whose save dialog answers `dialog`, and whose write is reported as `written`.
 * @param {any} dialog
 * @param {any} [written]
 */
function bridge(dialog, written = { available: true, result: true }) {
  return mockApi((method, path) => {
    if (path === '/api/bridge/save_file') return dialog;
    if (path === '/api/bridge/write_json_file') return written;
  });
}

describe('saveText', () => {
  it('writes the text where the user chose', async () => {
    const calls = bridge({ available: true, result: 'C:/out/a.txt' });

    expect(await saveText('hello', 'a.txt', TEXT)).toBe(true);

    expect(calls[0].body).toEqual({ filename: 'a.txt', file_types: ['Text files (*.txt)'] });
    expect(calls[1].body).toEqual({ path: 'C:/out/a.txt', text: 'hello' });
  });

  it('writes nothing when the user cancels', async () => {
    const calls = bridge({ available: true, result: null });

    expect(await saveText('hello', 'a.txt', TEXT)).toBe(false);

    expect(calls).toHaveLength(1);
  });

  it('says why the file could not be saved', async () => {
    bridge({ available: true, result: 'C:/out/a.txt' }, { available: false, reason: 'Disk full' });

    await expect(saveText('hello', 'a.txt', TEXT)).rejects.toThrow('Disk full');
  });

  it('downloads in the browser when there is no window', async () => {
    bridge({ available: false });
    const create = vi.fn(() => 'blob:x');
    const revoke = vi.fn();
    vi.spyOn(URL, 'createObjectURL').mockImplementation(create);
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(revoke);
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});

    expect(await saveText('hello', 'a.txt', TEXT)).toBe(true);

    expect(create).toHaveBeenCalledTimes(1);
    expect(click).toHaveBeenCalledTimes(1);
    expect(revoke).toHaveBeenCalledWith('blob:x');
  });
});

describe('saveJson', () => {
  it('saves the document as indented JSON', async () => {
    const calls = bridge({ available: true, result: 'C:/out/b.json' });

    await saveJson({ a: 1 }, 'b.json');

    expect(calls[0].body.file_types).toEqual(['JSON files (*.json)']);
    expect(calls[1].body.text).toBe('{\n  "a": 1\n}');
  });
});

describe('readJson', () => {
  it('reads a picked file as JSON', async () => {
    const file = new File(['{"a": [1, 2]}'], 'a.json', { type: 'application/json' });

    expect(await readJson(file)).toEqual({ a: [1, 2] });
  });

  it('refuses a file that is not JSON', async () => {
    await expect(readJson(new File(['nope'], 'a.json'))).rejects.toThrow();
  });
});

describe('fileNameFor', () => {
  it('names the file after the item and its kind', () => {
    expect(fileNameFor('My Brand')).toBe('My Brand.kodalo-brand.json');
    expect(fileNameFor('Wide', 'canvas')).toBe('Wide.kodalo-canvas.json');
  });

  it('drops characters Windows does not allow', () => {
    expect(fileNameFor('a/b:c*?')).toBe('abc.kodalo-brand.json');
  });

  it('falls back to the kind when nothing is left', () => {
    expect(fileNameFor('///', 'palette')).toBe('palette.kodalo-palette.json');
  });
});

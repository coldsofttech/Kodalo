import { useState } from 'react';
import {
  createPalette,
  deletePalette,
  duplicatePalette,
  exportPalette,
  importPalette,
  listPalettes,
  updatePalette,
} from '../../api.js';
import { setIn } from '../../brand.js';
import { useCatalog } from '../../catalog.js';
import { Button, TextField } from '../../components/controls.jsx';
import { ColorsPanel } from '../../components/editor.jsx';
import ImportButton from '../../components/ImportButton.jsx';
import { fileNameFor, readJson, saveJson } from '../../download.js';

const STRIP = ['background', 'primary', 'secondary', 'text', 'background_alt'];

/** Color a swatch through the CSSOM, since inline style attributes are not allowed. */
function paint(/** @type {string} */ color) {
  return (/** @type {HTMLElement | null} */ element) => {
    if (element) element.style.setProperty('background-color', color);
  };
}

/** @param {{ colors: any }} props */
function Strip({ colors }) {
  return (
    <span className="swatches" aria-hidden="true">
      {STRIP.map((key) => (
        <span key={key} className="swatch" ref={paint(colors[key].light)} />
      ))}
    </span>
  );
}

/**
 * What the form is doing: adding a palette, changing one, or copying one under a new name.
 * @typedef {{ kind: 'new' | 'edit' | 'copy', id: string, name: string, colors: any }} Form
 */

/**
 * @param {{ onChange?: () => void, revision?: number }} props `onChange` runs after a palette is
 *   added, changed or removed; `revision` changes when something else changed the lists.
 */
export default function PalettesPage({ onChange, revision = 0 }) {
  const { items, error, notice, busy, act, setError } = useCatalog(
    listPalettes,
    'Your palettes could not be loaded.',
    revision,
    onChange,
  );
  const [form, setForm] = useState(/** @type {Form | null} */ (null));
  const [asking, setAsking] = useState(/** @type {any | null} */ (null));

  async function submit() {
    if (!form) return;
    const { kind, id, name, colors } = form;
    const trimmed = name.trim();
    const saved = await act(
      () => {
        if (kind === 'new') return createPalette({ name: trimmed, colors });
        if (kind === 'copy') return duplicatePalette(id, trimmed);
        return updatePalette(id, { name: trimmed, colors });
      },
      kind === 'edit' ? `Saved "${trimmed}".` : `Created "${trimmed}".`,
    );
    if (saved) setForm(null);
  }

  async function exportOne(/** @type {any} */ palette) {
    try {
      saveJson(await exportPalette(palette.id), fileNameFor(palette.name, 'palette'));
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'The palette could not be exported.');
    }
  }

  async function importFile(/** @type {File} */ file) {
    let body;
    try {
      body = await readJson(file);
    } catch {
      setError('That file is not valid JSON.');
      return;
    }
    await act(() => importPalette(/** @type {object} */ (body)), 'Imported the palette.');
  }

  if (items === null) return <p>Loading palettes...</p>;

  const starter = items.find((item) => item.id === 'system-midnight') ?? items[0];
  const titles = { new: 'New palette', edit: 'Edit palette', copy: 'Copy palette' };
  return (
    <div className="palettes">
      <h1>Palettes</h1>
      <p>
        A palette is a named set of the eight brand colors. New brands start from one; a brand keeps
        its own copy of the colors, so changing a palette never changes a brand.
      </p>
      {error ? (
        <p role="alert" className="alert">
          {error}
        </p>
      ) : null}
      {notice ? (
        <p role="status" className="notice">
          {notice}
        </p>
      ) : null}

      {form ? (
        <section className="panel" aria-label={titles[form.kind]}>
          <h2>{titles[form.kind]}</h2>
          <TextField
            label="Palette name"
            value={form.name}
            maxLength={64}
            onChange={(name) => setForm((f) => f && { ...f, name })}
          />
          {form.kind === 'copy' ? (
            <p className="hint">A copy keeps the colors of the original.</p>
          ) : (
            <ColorsPanel
              data={{ colors: form.colors }}
              onChange={(path, value) =>
                setForm((f) =>
                  f ? { ...f, colors: setIn({ colors: f.colors }, path, value).colors } : f,
                )
              }
            />
          )}
          <div className="row actions">
            <Button appearance="accent" disabled={busy || !form.name.trim()} onClick={submit}>
              {form.kind === 'edit' ? 'Save palette' : 'Create palette'}
            </Button>
            <Button appearance="outline" disabled={busy} onClick={() => setForm(null)}>
              Cancel
            </Button>
          </div>
        </section>
      ) : (
        <div className="row actions">
          <Button
            appearance="accent"
            onClick={() =>
              setForm({ kind: 'new', id: '', name: '', colors: structuredClone(starter.colors) })
            }
          >
            New palette
          </Button>
          <ImportButton
            label="Import from file"
            what="palette"
            disabled={busy}
            onImport={importFile}
          />
        </div>
      )}

      {asking ? (
        <div className="ask" role="alertdialog" aria-label="Confirm delete">
          <span>Delete &quot;{asking.name}&quot;? Brands made from it keep their colors.</span>
          <Button
            appearance="accent"
            disabled={busy}
            onClick={async () => {
              await act(() => deletePalette(asking.id), `Deleted "${asking.name}".`);
              setAsking(null);
            }}
          >
            Delete palette
          </Button>
          <Button appearance="outline" onClick={() => setAsking(null)}>
            Keep it
          </Button>
        </div>
      ) : null}

      <table className="canvas-table">
        <caption className="visually-hidden">Palettes</caption>
        <thead>
          <tr>
            <th scope="col">Name</th>
            <th scope="col">Colors</th>
            <th scope="col">Type</th>
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map((palette) => (
            <tr key={palette.id}>
              <th scope="row">{palette.name}</th>
              <td>
                <Strip colors={palette.colors} />
              </td>
              <td>{palette.type === 'system' ? 'Built in' : 'Yours'}</td>
              <td>
                <div className="row-actions">
                  {palette.type === 'user' ? (
                    <Button
                      appearance="outline"
                      label={`Edit ${palette.name}`}
                      onClick={() =>
                        setForm({
                          kind: 'edit',
                          id: palette.id,
                          name: palette.name,
                          colors: structuredClone(palette.colors),
                        })
                      }
                    >
                      Edit
                    </Button>
                  ) : null}
                  <Button
                    appearance="outline"
                    label={`Copy ${palette.name}`}
                    onClick={() =>
                      setForm({
                        kind: 'copy',
                        id: palette.id,
                        name: `${palette.name} copy`.slice(0, 64),
                        colors: palette.colors,
                      })
                    }
                  >
                    Copy
                  </Button>
                  <Button
                    appearance="outline"
                    label={`Export ${palette.name}`}
                    onClick={() => exportOne(palette)}
                  >
                    Export
                  </Button>
                  {palette.type === 'user' ? (
                    <Button
                      appearance="outline"
                      label={`Delete ${palette.name}`}
                      onClick={() => setAsking(palette)}
                    >
                      Delete
                    </Button>
                  ) : null}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

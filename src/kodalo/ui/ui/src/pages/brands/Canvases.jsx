import { useState } from 'react';
import {
  createCanvas,
  deleteCanvas,
  duplicateCanvas,
  exportCanvas,
  importCanvas,
  listCanvases,
  updateCanvas,
} from '../../api.js';
import { useCatalog } from '../../catalog.js';
import { Button, NumberField, TextField } from '../../components/controls.jsx';
import ImportButton from '../../components/ImportButton.jsx';
import { fileNameFor, readJson, saveJson } from '../../download.js';

const EMPTY = { name: '', width: 1080, height: 1350 };

/**
 * What the form is doing: adding a canvas, changing one, or copying one under a new name.
 * @typedef {{ kind: 'new' | 'edit' | 'copy', id: string, name: string, width: number, height: number }} Form
 */

/**
 * @param {{ onChange?: () => void, revision?: number }} props `onChange` runs after a canvas is
 *   added, changed or removed; `revision` changes when something else changed the lists.
 */
export default function CanvasesPage({ onChange, revision = 0 }) {
  const { items, error, notice, busy, act, setError } = useCatalog(
    listCanvases,
    'Your canvases could not be loaded.',
    revision,
    onChange,
  );
  const [form, setForm] = useState(/** @type {Form | null} */ (null));
  const [asking, setAsking] = useState(/** @type {any | null} */ (null));

  async function submit() {
    if (!form) return;
    const { kind, id, name, width, height } = form;
    const trimmed = name.trim();
    const saved = await act(
      () => {
        if (kind === 'new') return createCanvas({ name: trimmed, width, height });
        if (kind === 'copy') return duplicateCanvas(id, trimmed);
        return updateCanvas(id, { name: trimmed, width, height });
      },
      kind === 'edit' ? `Saved "${trimmed}".` : `Created "${trimmed}".`,
    );
    if (saved) setForm(null);
  }

  async function exportOne(/** @type {any} */ canvas) {
    try {
      saveJson(await exportCanvas(canvas.id), fileNameFor(canvas.name, 'canvas'));
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'The canvas could not be exported.');
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
    await act(async () => {
      const made = await importCanvas(/** @type {object} */ (body));
      return made;
    }, 'Imported the canvas.');
  }

  if (items === null) return <p>Loading canvases...</p>;

  const titles = { new: 'New canvas', edit: 'Edit canvas', copy: 'Copy canvas' };
  return (
    <div className="canvases">
      <h1>Canvases</h1>
      <p>
        A canvas is a named slide size. Create one here, then use it in a layout. Changing a canvas
        changes every layout, and so every brand, that uses it.
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
            label="Canvas name"
            value={form.name}
            maxLength={64}
            onChange={(name) => setForm((f) => f && { ...f, name })}
          />
          <div className="row">
            <NumberField
              label="Width (pixels)"
              value={form.width}
              min={200}
              max={4000}
              onChange={(width) => setForm((f) => f && { ...f, width })}
            />
            <NumberField
              label="Height (pixels)"
              value={form.height}
              min={200}
              max={4000}
              onChange={(height) => setForm((f) => f && { ...f, height })}
            />
          </div>
          {form.kind === 'copy' ? (
            <p className="hint">A copy keeps the size of the original.</p>
          ) : null}
          <div className="row actions">
            <Button appearance="accent" disabled={busy || !form.name.trim()} onClick={submit}>
              {form.kind === 'edit' ? 'Save canvas' : 'Create canvas'}
            </Button>
            <Button appearance="outline" disabled={busy} onClick={() => setForm(null)}>
              Cancel
            </Button>
          </div>
        </section>
      ) : (
        <div className="row actions">
          <Button appearance="accent" onClick={() => setForm({ kind: 'new', id: '', ...EMPTY })}>
            New canvas
          </Button>
          <ImportButton
            label="Import from file"
            what="canvas"
            disabled={busy}
            onImport={importFile}
          />
        </div>
      )}

      {asking ? (
        <div className="ask" role="alertdialog" aria-label="Confirm delete">
          <span>Delete &quot;{asking.name}&quot;?</span>
          <Button
            appearance="accent"
            disabled={busy}
            onClick={async () => {
              await act(() => deleteCanvas(asking.id), `Deleted "${asking.name}".`);
              setAsking(null);
            }}
          >
            Delete canvas
          </Button>
          <Button appearance="outline" onClick={() => setAsking(null)}>
            Keep it
          </Button>
        </div>
      ) : null}

      <table className="canvas-table">
        <caption className="visually-hidden">Canvases</caption>
        <thead>
          <tr>
            <th scope="col">Name</th>
            <th scope="col">Size</th>
            <th scope="col">Type</th>
            <th scope="col">Used by layouts</th>
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map((canvas) => (
            <tr key={canvas.id}>
              <th scope="row">{canvas.name}</th>
              <td>
                {canvas.width} x {canvas.height}
              </td>
              <td>{canvas.type === 'system' ? 'Built in' : 'Yours'}</td>
              <td>{canvas.used_by.length ? canvas.used_by.join(', ') : 'No layout'}</td>
              <td>
                <div className="row-actions">
                  {canvas.type === 'user' ? (
                    <Button
                      appearance="outline"
                      label={`Edit ${canvas.name}`}
                      onClick={() => setForm({ kind: 'edit', ...pick(canvas) })}
                    >
                      Edit
                    </Button>
                  ) : null}
                  <Button
                    appearance="outline"
                    label={`Copy ${canvas.name}`}
                    onClick={() =>
                      setForm({
                        kind: 'copy',
                        ...pick(canvas),
                        name: `${canvas.name} copy`.slice(0, 64),
                      })
                    }
                  >
                    Copy
                  </Button>
                  <Button
                    appearance="outline"
                    label={`Export ${canvas.name}`}
                    onClick={() => exportOne(canvas)}
                  >
                    Export
                  </Button>
                  {canvas.type === 'user' ? (
                    <Button
                      appearance="outline"
                      label={`Delete ${canvas.name}`}
                      onClick={() => setAsking(canvas)}
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

const pick = (/** @type {any} */ { id, name, width, height }) => ({ id, name, width, height });

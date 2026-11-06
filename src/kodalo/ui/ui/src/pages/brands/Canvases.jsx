import { useEffect, useState } from 'react';
import {
  createCanvas,
  deleteCanvas,
  duplicateCanvas,
  exportCanvas,
  importCanvas,
  listCanvases,
  listSocialPlatforms,
  updateCanvas,
} from '../../api.js';
import { useCatalog } from '../../catalog.js';
import { Button, NumberField, Select, TextField } from '../../components/controls.jsx';
import ImportButton from '../../components/ImportButton.jsx';
import { fileNameFor, readJson, saveJson } from '../../download.js';

const EMPTY = { name: '', width: 1080, height: 1350, platform_id: 'instagram' };

/**
 * The warning for a size the platform does not recommend, or '' when it is fine. It mirrors the
 * server's wording, so the form can warn while the user types.
 * @param {any[]} platforms @param {string} platformId @param {number} width @param {number} height
 */
function concernFor(platforms, platformId, width, height) {
  const platform = platforms.find((item) => item.id === platformId);
  if (!platform || platform.sizes.length === 0) return '';
  if (platform.sizes.some((size) => size.width === width && size.height === height)) return '';
  const options = platform.sizes.map((size) => `${size.width} x ${size.height}`).join(', ');
  return `${platform.name} recommends ${options}. ${width} x ${height} may be cropped or resized.`;
}

/**
 * What the form is doing: adding a canvas, changing one, or copying one under a new name.
 * @typedef {{ kind: 'new' | 'edit' | 'copy', id: string, name: string, width: number, height: number, platform_id: string }} Form
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
  const [platforms, setPlatforms] = useState(/** @type {any[]} */ ([]));

  useEffect(() => {
    listSocialPlatforms()
      .then(setPlatforms)
      .catch((failure) =>
        setError(failure instanceof Error ? failure.message : 'The platforms could not be loaded.'),
      );
  }, [setError]);

  async function submit() {
    if (!form) return;
    const { kind, id, name, width, height, platform_id } = form;
    const trimmed = name.trim();
    const saved = await act(
      () => {
        if (kind === 'new') return createCanvas({ name: trimmed, width, height, platform_id });
        if (kind === 'copy') return duplicateCanvas(id, trimmed);
        return updateCanvas(id, { name: trimmed, width, height, platform_id });
      },
      kind === 'edit' ? `Saved "${trimmed}".` : `Created "${trimmed}".`,
    );
    if (saved) setForm(null);
  }

  async function exportOne(/** @type {any} */ canvas) {
    try {
      await saveJson(await exportCanvas(canvas.id), fileNameFor(canvas.name, 'canvas'));
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
          <Select
            label="Social platform"
            value={form.platform_id}
            onChange={(platform_id) => setForm((f) => f && { ...f, platform_id })}
          >
            {platforms.map((platform) => (
              <option key={platform.id} value={platform.id}>
                {platform.name}
              </option>
            ))}
          </Select>
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
          {concernFor(platforms, form.platform_id, form.width, form.height) ? (
            <p role="status" className="warning">
              <i className="bi bi-exclamation-triangle-fill" aria-hidden="true" />{' '}
              {concernFor(platforms, form.platform_id, form.width, form.height)} You can still save
              it.
            </p>
          ) : null}
          {form.kind === 'copy' ? (
            <p className="hint">A copy keeps the size and platform of the original.</p>
          ) : null}
          <div className="row actions">
            <Button
              appearance="accent"
              label={form.kind === 'edit' ? 'Save canvas' : 'Create canvas'}
              title={form.kind === 'edit' ? 'Save canvas' : 'Create canvas'}
              disabled={busy || !form.name.trim()}
              onClick={submit}
            >
              <i
                className={`bi ${form.kind === 'edit' ? 'bi-floppy' : 'bi-check-lg'}`}
                aria-hidden="true"
              />
            </Button>
            <Button
              appearance="outline"
              label="Cancel"
              title="Cancel"
              disabled={busy}
              onClick={() => setForm(null)}
            >
              <i className="bi bi-x-lg" aria-hidden="true" />
            </Button>
          </div>
        </section>
      ) : (
        <div className="row actions">
          <Button
            appearance="accent"
            label="New canvas"
            title="New canvas"
            onClick={() => setForm({ kind: 'new', id: '', ...EMPTY })}
          >
            <i className="bi bi-plus-lg" aria-hidden="true" />
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
            danger
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
            <th scope="col">Platform</th>
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
              <td>{canvas.platform}</td>
              <td>
                {canvas.width} x {canvas.height}
                {canvas.size_concern ? (
                  <i
                    className="bi bi-exclamation-triangle-fill size-concern"
                    role="img"
                    aria-label={canvas.size_concern}
                    title={canvas.size_concern}
                  />
                ) : null}
              </td>
              <td>{canvas.type === 'system' ? 'Built in' : 'Yours'}</td>
              <td>{canvas.used_by.length ? canvas.used_by.join(', ') : 'No layout'}</td>
              <td>
                <div className="row-actions">
                  {canvas.type === 'user' ? (
                    <Button
                      appearance="outline"
                      label={`Edit ${canvas.name}`}
                      title="Edit"
                      onClick={() => setForm({ kind: 'edit', ...pick(canvas) })}
                    >
                      <i className="bi bi-pencil" aria-hidden="true" />
                    </Button>
                  ) : null}
                  <Button
                    appearance="outline"
                    label={`Copy ${canvas.name}`}
                    title="Copy"
                    onClick={() =>
                      setForm({
                        kind: 'copy',
                        ...pick(canvas),
                        name: `${canvas.name} copy`.slice(0, 64),
                      })
                    }
                  >
                    <i className="bi bi-copy" aria-hidden="true" />
                  </Button>
                  <Button
                    appearance="outline"
                    label={`Export ${canvas.name}`}
                    title="Export"
                    onClick={() => exportOne(canvas)}
                  >
                    <i className="bi bi-box-arrow-up" aria-hidden="true" />
                  </Button>
                  {canvas.type === 'user' ? (
                    <Button
                      appearance="outline"
                      danger
                      label={`Delete ${canvas.name}`}
                      title="Delete"
                      onClick={() => setAsking(canvas)}
                    >
                      <i className="bi bi-trash" aria-hidden="true" />
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

const pick = (/** @type {any} */ { id, name, width, height, platform_id }) => ({
  id,
  name,
  width,
  height,
  platform_id,
});

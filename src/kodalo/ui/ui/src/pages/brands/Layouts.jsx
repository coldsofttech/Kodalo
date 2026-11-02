import { useState } from 'react';
import {
  createLayout,
  deleteLayout,
  duplicateLayout,
  exportLayout,
  importLayout,
  listCanvases,
  listLayouts,
  updateLayout,
} from '../../api.js';
import { useCatalog } from '../../catalog.js';
import { Button, NumberField, Select, Switch, TextField } from '../../components/controls.jsx';
import ImportButton from '../../components/ImportButton.jsx';
import { fileNameFor, readJson, saveJson } from '../../download.js';

const SETTINGS = [
  'canvas_id',
  'margin_top',
  'margin_side',
  'margin_bottom',
  'corner_radius',
  'slide_numbers',
  'footer_text',
  'align',
  'density',
  'slides_count',
];

/** The settings a layout decides, taken from a stored layout. @param {any} layout */
const settingsOf = (layout) => Object.fromEntries(SETTINGS.map((key) => [key, layout[key]]));

/**
 * What the form is doing: adding a layout, changing one, or copying one under a new name.
 * @typedef {{ kind: 'new' | 'edit' | 'copy', id: string, name: string, settings: Record<string, any> }} Form
 */

/**
 * @param {{ onChange?: () => void, revision?: number }} props `onChange` runs after a layout is
 *   added, changed or removed; `revision` changes when something else changed the lists.
 */
export default function LayoutsPage({ onChange, revision = 0 }) {
  const { items, error, notice, busy, act, setError } = useCatalog(
    listLayouts,
    'Your layouts could not be loaded.',
    revision,
    onChange,
  );
  const canvasList = useCatalog(listCanvases, 'The canvases could not be loaded.', revision);
  const [form, setForm] = useState(/** @type {Form | null} */ (null));
  const [asking, setAsking] = useState(/** @type {any | null} */ (null));

  const canvases = canvasList.items ?? [];
  const canvasName = (/** @type {string} */ id) => {
    const canvas = canvases.find((item) => item.id === id);
    return canvas ? `${canvas.name} (${canvas.width} x ${canvas.height})` : id;
  };

  async function submit() {
    if (!form) return;
    const { kind, id, name, settings } = form;
    const trimmed = name.trim();
    const saved = await act(
      () => {
        if (kind === 'new') return createLayout({ name: trimmed, settings });
        if (kind === 'copy') return duplicateLayout(id, trimmed);
        return updateLayout(id, { name: trimmed, ...settings });
      },
      kind === 'edit' ? `Saved "${trimmed}".` : `Created "${trimmed}".`,
    );
    if (saved) setForm(null);
  }

  async function exportOne(/** @type {any} */ layout) {
    try {
      saveJson(await exportLayout(layout.id), fileNameFor(layout.name, 'layout'));
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'The layout could not be exported.');
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
    await act(() => importLayout(/** @type {object} */ (body)), 'Imported the layout.');
  }

  if (items === null) return <p>Loading layouts...</p>;

  const starter = items.find((item) => item.id === 'system-default') ?? items[0];
  const set = (/** @type {string} */ key, /** @type {unknown} */ value) =>
    setForm((f) => f && { ...f, settings: { ...f.settings, [key]: value } });
  const titles = { new: 'New layout', edit: 'Edit layout', copy: 'Copy layout' };
  return (
    <div className="layouts">
      <h1>Layouts</h1>
      <p>
        A layout is a named set of slide settings: the canvas, margins, corner radius, text and the
        number of slides. Brands share layouts, so changing a layout changes every brand that uses
        it.
      </p>
      {error || canvasList.error ? (
        <p role="alert" className="alert">
          {error || canvasList.error}
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
            label="Layout name"
            value={form.name}
            maxLength={64}
            onChange={(name) => setForm((f) => f && { ...f, name })}
          />
          {form.kind === 'copy' ? (
            <p className="hint">A copy keeps the settings of the original.</p>
          ) : (
            <>
              <Select
                label="Canvas"
                value={form.settings.canvas_id}
                onChange={(value) => set('canvas_id', value)}
              >
                {canvases.map((canvas) => (
                  <option key={canvas.id} value={canvas.id}>
                    {canvas.name} ({canvas.width} x {canvas.height})
                  </option>
                ))}
              </Select>
              <NumberField
                label="Number of slides"
                value={form.settings.slides_count}
                min={1}
                max={30}
                onChange={(value) => set('slides_count', value)}
              />
              <div className="row">
                <NumberField
                  label="Top margin"
                  value={form.settings.margin_top}
                  min={0}
                  max={400}
                  onChange={(value) => set('margin_top', value)}
                />
                <NumberField
                  label="Side margin"
                  value={form.settings.margin_side}
                  min={0}
                  max={400}
                  onChange={(value) => set('margin_side', value)}
                />
                <NumberField
                  label="Bottom margin"
                  value={form.settings.margin_bottom}
                  min={0}
                  max={400}
                  onChange={(value) => set('margin_bottom', value)}
                />
              </div>
              <NumberField
                label="Corner radius"
                value={form.settings.corner_radius}
                min={0}
                max={200}
                onChange={(value) => set('corner_radius', value)}
              />
              <TextField
                label="Footer text"
                value={form.settings.footer_text}
                maxLength={120}
                onChange={(value) => set('footer_text', value)}
              />
              <Switch
                label="Show slide numbers"
                checked={form.settings.slide_numbers}
                onChange={(value) => set('slide_numbers', value)}
              />
              <div className="row">
                <Select
                  label="Text alignment"
                  value={form.settings.align}
                  onChange={(value) => set('align', value)}
                >
                  <option value="left">Left</option>
                  <option value="center">Center</option>
                </Select>
                <Select
                  label="Spacing"
                  value={form.settings.density}
                  onChange={(value) => set('density', value)}
                >
                  <option value="compact">Compact</option>
                  <option value="regular">Regular</option>
                  <option value="spacious">Spacious</option>
                </Select>
              </div>
            </>
          )}
          <div className="row actions">
            <Button appearance="accent" disabled={busy || !form.name.trim()} onClick={submit}>
              {form.kind === 'edit' ? 'Save layout' : 'Create layout'}
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
              setForm({ kind: 'new', id: '', name: '', settings: settingsOf(starter) })
            }
          >
            New layout
          </Button>
          <ImportButton
            label="Import from file"
            what="layout"
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
              await act(() => deleteLayout(asking.id), `Deleted "${asking.name}".`);
              setAsking(null);
            }}
          >
            Delete layout
          </Button>
          <Button appearance="outline" onClick={() => setAsking(null)}>
            Keep it
          </Button>
        </div>
      ) : null}

      <table className="canvas-table">
        <caption className="visually-hidden">Layouts</caption>
        <thead>
          <tr>
            <th scope="col">Name</th>
            <th scope="col">Canvas</th>
            <th scope="col">Slides</th>
            <th scope="col">Type</th>
            <th scope="col">Used by brands</th>
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map((layout) => (
            <tr key={layout.id}>
              <th scope="row">{layout.name}</th>
              <td>{canvasName(layout.canvas_id)}</td>
              <td>{layout.slides_count}</td>
              <td>{layout.type === 'system' ? 'Built in' : 'Yours'}</td>
              <td>{layout.used_by.length ? layout.used_by.join(', ') : 'No brand'}</td>
              <td>
                <div className="row-actions">
                  {layout.type === 'user' ? (
                    <Button
                      appearance="outline"
                      label={`Edit ${layout.name}`}
                      onClick={() =>
                        setForm({
                          kind: 'edit',
                          id: layout.id,
                          name: layout.name,
                          settings: settingsOf(layout),
                        })
                      }
                    >
                      Edit
                    </Button>
                  ) : null}
                  <Button
                    appearance="outline"
                    label={`Copy ${layout.name}`}
                    onClick={() =>
                      setForm({
                        kind: 'copy',
                        id: layout.id,
                        name: `${layout.name} copy`.slice(0, 64),
                        settings: settingsOf(layout),
                      })
                    }
                  >
                    Copy
                  </Button>
                  <Button
                    appearance="outline"
                    label={`Export ${layout.name}`}
                    onClick={() => exportOne(layout)}
                  >
                    Export
                  </Button>
                  {layout.type === 'user' ? (
                    <Button
                      appearance="outline"
                      label={`Delete ${layout.name}`}
                      onClick={() => setAsking(layout)}
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

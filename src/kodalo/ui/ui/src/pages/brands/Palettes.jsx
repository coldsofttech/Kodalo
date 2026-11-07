import { useState } from 'react';
import {
  createPalette,
  deletePalette,
  duplicatePalette,
  exportPalette,
  importPalette,
  listPalettes,
  planPaletteSuggestion,
  suggestPalette,
  updatePalette,
} from '../../libs/api.js';
import { setIn } from '../../libs/brand.js';
import { useCatalog } from '../../libs/catalog.js';
import AiOverlay from '../../components/AiOverlay.jsx';
import { Button, TextField } from '../../components/controls.jsx';
import { ColorsPanel } from '../../components/editor.jsx';
import ImportButton from '../../components/ImportButton.jsx';
import { fileNameFor, readJson, saveJson } from '../../libs/download.js';
import { get } from '../../libs/lookup.js';

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
        <span key={key} className="swatch" ref={paint(get(colors, key).light)} />
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
  const [suggesting, setSuggesting] = useState(false);
  /** True while the AI is working on the palette, to show the overlay. */
  const [thinking, setThinking] = useState(false);
  /** What the AI would be sent and cost, while the user decides whether to go ahead. */
  const [plan, setPlan] = useState(/** @type {any | null} */ (null));

  async function ask() {
    setSuggesting(true);
    try {
      setPlan(await planPaletteSuggestion());
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'The AI could not be reached.');
    } finally {
      setSuggesting(false);
    }
  }

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

  async function suggest() {
    setPlan(null);
    setSuggesting(true);
    setThinking(true);
    try {
      const { name, colors } = await suggestPalette();
      setForm((f) => f && { ...f, name, colors });
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'The AI could not suggest a palette.');
    } finally {
      setSuggesting(false);
      setThinking(false);
    }
  }

  async function exportOne(/** @type {any} */ palette) {
    try {
      await saveJson(await exportPalette(palette.id), fileNameFor(palette.name, 'palette'));
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
      {thinking ? <AiOverlay message="The AI is choosing colors…" /> : null}
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
            <Button
              appearance="accent"
              label={form.kind === 'edit' ? 'Save palette' : 'Create palette'}
              title={form.kind === 'edit' ? 'Save palette' : 'Create palette'}
              disabled={busy || !form.name.trim()}
              onClick={submit}
            >
              <i
                className={`bi ${form.kind === 'edit' ? 'bi-floppy' : 'bi-check-lg'}`}
                aria-hidden="true"
              />
            </Button>
            {form.kind === 'new' ? (
              <Button
                className="ai-button"
                label="Suggest with AI"
                title="Suggest with AI"
                disabled={busy || suggesting || plan !== null}
                onClick={ask}
              >
                <i
                  className={`bi ${suggesting ? 'bi-hourglass-split' : 'bi-stars'}`}
                  aria-hidden="true"
                />
              </Button>
            ) : null}
            <Button
              appearance="outline"
              label="Cancel"
              title="Cancel"
              disabled={busy}
              onClick={() => {
                setPlan(null);
                setForm(null);
              }}
            >
              <i className="bi bi-x-lg" aria-hidden="true" />
            </Button>
          </div>
          {plan ? (
            <div role="group" aria-labelledby="palette-plan-title" className="confirm">
              <h3 id="palette-plan-title">Ask {plan.label || 'the AI'} for a palette?</h3>
              <p>
                Kodalo will send the names and colors of your {plan.palettes} existing palettes, so
                the AI suggests one that is different. Nothing else is sent. The suggestion fills
                this form and is not saved until you create it.
              </p>
              <p>
                It goes to {plan.label} ({plan.model}). About {plan.input_tokens} tokens sent, and
                at most {plan.max_output_tokens} tokens in the answer.
              </p>
              <div className="row actions">
                <Button
                  appearance="accent"
                  label="Proceed"
                  title="Proceed"
                  disabled={suggesting}
                  onClick={suggest}
                >
                  <i className="bi bi-check-lg" aria-hidden="true" />
                </Button>
                <Button
                  label="Cancel"
                  title="Cancel"
                  disabled={suggesting}
                  onClick={() => setPlan(null)}
                >
                  <i className="bi bi-x-lg" aria-hidden="true" />
                </Button>
              </div>
            </div>
          ) : null}
        </section>
      ) : (
        <div className="row actions">
          <Button
            appearance="accent"
            label="New palette"
            title="New palette"
            onClick={() =>
              setForm({ kind: 'new', id: '', name: '', colors: structuredClone(starter.colors) })
            }
          >
            <i className="bi bi-plus-lg" aria-hidden="true" />
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
            danger
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
                      title="Edit"
                      onClick={() =>
                        setForm({
                          kind: 'edit',
                          id: palette.id,
                          name: palette.name,
                          colors: structuredClone(palette.colors),
                        })
                      }
                    >
                      <i className="bi bi-pencil" aria-hidden="true" />
                    </Button>
                  ) : null}
                  <Button
                    appearance="outline"
                    label={`Copy ${palette.name}`}
                    title="Copy"
                    onClick={() =>
                      setForm({
                        kind: 'copy',
                        id: palette.id,
                        name: `${palette.name} copy`.slice(0, 64),
                        colors: palette.colors,
                      })
                    }
                  >
                    <i className="bi bi-copy" aria-hidden="true" />
                  </Button>
                  <Button
                    appearance="outline"
                    label={`Export ${palette.name}`}
                    title="Export"
                    onClick={() => exportOne(palette)}
                  >
                    <i className="bi bi-box-arrow-up" aria-hidden="true" />
                  </Button>
                  {palette.type === 'user' ? (
                    <Button
                      appearance="outline"
                      danger
                      label={`Delete ${palette.name}`}
                      title="Delete"
                      onClick={() => setAsking(palette)}
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

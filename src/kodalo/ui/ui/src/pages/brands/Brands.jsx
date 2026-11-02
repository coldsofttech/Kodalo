import { useCallback, useEffect, useRef, useState } from 'react';
import {
  createBrand,
  createPalette,
  deleteBrand,
  duplicateBrand,
  exportBrand,
  importBrand,
  listBrands,
  listCanvases,
  listFonts,
  listLayouts,
  listPalettes,
  setDefaultBrand,
  updateBrand,
} from '../../api.js';
import { sameData, setIn } from '../../brand.js';
import { Button, TextField } from '../../components/controls.jsx';
import { ColorsPanel, FontsPanel, LayoutPanel, LogoPanel } from '../../components/editor.jsx';
import NewBrand from '../../components/NewBrand.jsx';
import Preview from '../../components/preview.jsx';
import { fileNameFor, readJson, saveJson } from '../../download.js';

const TABS = [
  ['colors', 'Colors'],
  ['fonts', 'Fonts'],
  ['logo', 'Logo'],
  ['layout', 'Layout'],
];

const errorText = (/** @type {unknown} */ error, /** @type {string} */ fallback) =>
  error instanceof Error ? error.message : fallback;

/** The draft is what the form edits; the saved brand is what the server holds. */
const toDraft = (/** @type {any} */ brand) => ({ name: brand.name, data: brand.data });

/** @param {{ busy: boolean, onSave: (name: string) => Promise<unknown> }} props */
function SavePalette({ busy, onSave }) {
  const [name, setName] = useState('');
  return (
    <section className="panel" aria-label="Save as palette">
      <h3>Save these colors as a palette</h3>
      <p className="hint">
        A palette can start new brands. Manage palettes under Brands, Palettes.
      </p>
      <div className="row">
        <TextField label="Palette name" value={name} maxLength={64} onChange={setName} />
        <Button
          appearance="outline"
          disabled={busy || !name.trim()}
          onClick={async () => {
            await onSave(name.trim());
            setName('');
          }}
        >
          Save palette
        </Button>
      </div>
    </section>
  );
}

/** @param {{ onImport: (file: File) => void }} props */
function ImportButton({ onImport }) {
  const input = useRef(/** @type {HTMLInputElement | null} */ (null));
  return (
    <>
      <input
        ref={input}
        type="file"
        accept="application/json,.json"
        className="visually-hidden"
        aria-label="Choose a brand file to import"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onImport(file);
          event.target.value = '';
        }}
      />
      <Button appearance="outline" onClick={() => input.current?.click()}>
        Import from file
      </Button>
    </>
  );
}

/**
 * @param {{ catalogRevision?: number, onCatalogChange?: () => void }} props `catalogRevision`
 *   changes when canvases, layouts or palettes do; `onCatalogChange` runs when this page saves a palette.
 */
export default function BrandsPage({ catalogRevision = 0, onCatalogChange }) {
  const [brands, setBrands] = useState(/** @type {any[] | null} */ (null));
  const [palettes, setPalettes] = useState(/** @type {any[]} */ ([]));
  const [fonts, setFonts] = useState(/** @type {any[]} */ ([]));
  const [canvases, setCanvases] = useState(/** @type {any[]} */ ([]));
  const [layouts, setLayouts] = useState(/** @type {any[]} */ ([]));
  const [selectedId, setSelectedId] = useState(/** @type {string | null} */ (null));
  const [draft, setDraft] = useState(/** @type {{ name: string, data: any } | null} */ (null));
  const [tab, setTab] = useState('colors');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  /** What is waiting for a yes or no: leaving with unsaved changes, deleting, or naming a copy. */
  const [asking, setAsking] = useState(
    /** @type {null | { kind: 'switch', id: string } | { kind: 'delete' } | { kind: 'duplicate', name: string } | { kind: 'new' }} */ (
      null
    ),
  );

  const select = useCallback((/** @type {any[]} */ list, /** @type {string | null} */ id) => {
    const brand =
      list.find((item) => item.id === id) ?? list.find((item) => item.is_default) ?? list[0];
    setSelectedId(brand ? brand.id : null);
    setDraft(brand ? toDraft(brand) : null);
  }, []);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [list, palettesList, fontsList, canvasList, layoutList] = await Promise.all([
          listBrands(),
          listPalettes(),
          listFonts(),
          listCanvases(),
          listLayouts(),
        ]);
        if (!alive) return;
        setBrands(list);
        setPalettes(palettesList);
        setFonts(fontsList);
        setCanvases(canvasList);
        setLayouts(layoutList);
        select(list, null);
      } catch (failure) {
        if (alive) {
          setBrands([]);
          setError(errorText(failure, 'Your brands could not be loaded.'));
        }
      }
    })();
    return () => {
      alive = false;
    };
  }, [select]);

  useEffect(() => {
    if (catalogRevision === 0) return undefined;
    let alive = true;
    Promise.all([listCanvases(), listLayouts(), listPalettes()]).then(
      ([canvasList, layoutList, palettesList]) => {
        if (!alive) return;
        setCanvases(canvasList);
        setLayouts(layoutList);
        setPalettes(palettesList);
      },
      (failure) => alive && setError(errorText(failure, 'The lists could not be loaded.')),
    );
    return () => {
      alive = false;
    };
  }, [catalogRevision]);

  useEffect(() => {
    if (!notice) return undefined;
    const timer = setTimeout(() => setNotice(''), 5000);
    return () => clearTimeout(timer);
  }, [notice]);

  const selected = brands?.find((item) => item.id === selectedId) ?? null;
  const dirty = Boolean(selected && draft && !sameData(toDraft(selected), draft));

  /** Run a call that changes things: show its error, or its notice when it works. */
  async function act(
    /** @type {() => Promise<string | void>} */ task,
    /** @type {string} */ fallback,
  ) {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const message = await task();
      if (message) setNotice(message);
    } catch (failure) {
      setError(errorText(failure, fallback));
    } finally {
      setBusy(false);
    }
  }

  function replace(/** @type {any} */ brand) {
    setBrands((list) => (list ?? []).map((item) => (item.id === brand.id ? brand : item)));
  }

  async function refreshAndSelect(/** @type {string} */ id) {
    const list = await listBrands();
    setBrands(list);
    select(list, id);
    setAsking(null);
  }

  const edit = (/** @type {string} */ path, /** @type {unknown} */ value) =>
    setDraft((current) => current && { ...current, data: setIn(current.data, path, value) });

  const chooseBrand = (/** @type {string} */ id) => {
    setError('');
    setNotice('');
    if (dirty) {
      setAsking({ kind: 'switch', id });
    } else {
      select(brands ?? [], id);
      setAsking(null);
    }
  };

  const save = () =>
    act(async () => {
      if (!selected || !draft) return;
      const stored = await updateBrand(selected.id, { name: draft.name, data: draft.data });
      replace(stored);
      setDraft(toDraft(stored));
      return 'Saved.';
    }, 'The brand could not be saved.');

  const discard = () => {
    if (selected) setDraft(toDraft(selected));
    setError('');
    setNotice('');
  };

  const onLogoStored = (/** @type {any} */ stored) => {
    replace(stored);
    setDraft(
      (current) =>
        current && {
          ...current,
          data: setIn(
            setIn(current.data, 'logo.file', stored.data.logo.file),
            'logo.dark_file',
            stored.data.logo.dark_file,
          ),
        },
    );
  };

  const create = (/** @type {string} */ name, /** @type {string} */ palette) =>
    act(async () => {
      const created = await createBrand({ name, palette });
      await refreshAndSelect(created.id);
      return `Created ${created.name}.`;
    }, 'The brand could not be created.');

  const importFile = (/** @type {File} */ file) =>
    act(async () => {
      let document;
      try {
        document = await readJson(file);
      } catch {
        throw new Error('That file is not a Kodalo brand file.');
      }
      const imported = await importBrand(/** @type {object} */ (document));
      await refreshAndSelect(imported.id);
      return `Imported ${imported.name}.`;
    }, 'The brand could not be imported.');

  if (brands === null) return <p role="status">Loading your brands...</p>;

  if (brands.length === 0) {
    return (
      <section className="welcome card" aria-labelledby="welcome-title">
        <h1 id="welcome-title">Welcome to Kodalo</h1>
        <p>
          Kodalo turns your GitHub projects into on-brand Instagram posts. Everything stays on this
          computer. Start by choosing the look your posts should have. You can change every detail
          afterwards.
        </p>
        {error ? (
          <p role="alert" className="alert">
            {error}
          </p>
        ) : null}
        <NewBrand firstRun palettes={palettes} busy={busy} onCreate={create} />
        <p className="hint">Already have a brand file?</p>
        <ImportButton onImport={importFile} />
      </section>
    );
  }

  const current = draft && selected ? { brand: selected, ...draft } : null;
  /** The canvas the draft's layout points to; the saved brand's canvas until the list is loaded. */
  const layoutOf = (/** @type {NonNullable<typeof current>} */ item) =>
    layouts.find((layout) => layout.id === item.data.layout_id) ?? item.brand.layout;
  const canvasOf = (/** @type {NonNullable<typeof current>} */ item) =>
    canvases.find((canvas) => canvas.id === layoutOf(item).canvas_id) ?? item.brand.canvas;
  return (
    <div className="brands">
      <aside className="profiles" aria-label="Brand profiles">
        <h2>Brands</h2>
        <ul>
          {brands.map((brand) => (
            <li key={brand.id}>
              <button
                type="button"
                className="profile"
                aria-current={brand.id === selectedId ? 'true' : undefined}
                onClick={() => chooseBrand(brand.id)}
              >
                {brand.name}
                {brand.is_default ? <span className="badge">Default</span> : null}
              </button>
            </li>
          ))}
        </ul>
        <div className="stack">
          <Button appearance="accent" onClick={() => setAsking({ kind: 'new' })}>
            New brand
          </Button>
          <ImportButton onImport={importFile} />
        </div>
      </aside>

      <section className="editor" aria-label="Brand editor">
        {asking?.kind === 'new' ? (
          <div className="ask" role="group" aria-label="New brand">
            <NewBrand palettes={palettes} busy={busy} onCreate={create} />
            <Button appearance="outline" onClick={() => setAsking(null)}>
              Cancel
            </Button>
          </div>
        ) : null}
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
        {current ? (
          <>
            <header className="editor-head">
              <TextField
                label="Brand name"
                value={current.name}
                maxLength={64}
                onChange={(name) => setDraft((d) => d && { ...d, name })}
              />
              <div className="row actions">
                {!current.brand.is_default ? (
                  <Button
                    disabled={busy || dirty}
                    onClick={() =>
                      act(async () => {
                        replace(await setDefaultBrand(current.brand.id));
                        const list = await listBrands();
                        setBrands(list);
                        return 'Default brand changed.';
                      }, 'The default could not be changed.')
                    }
                  >
                    Make default
                  </Button>
                ) : null}
                <Button
                  disabled={busy || dirty}
                  onClick={() =>
                    setAsking({ kind: 'duplicate', name: `${current.brand.name} copy` })
                  }
                >
                  Duplicate
                </Button>
                <Button
                  disabled={busy || dirty}
                  onClick={() =>
                    act(async () => {
                      saveJson(
                        await exportBrand(current.brand.id),
                        fileNameFor(current.brand.name),
                      );
                      return 'Exported. Check your downloads.';
                    }, 'The brand could not be exported.')
                  }
                >
                  Export
                </Button>
                <Button
                  appearance="outline"
                  disabled={busy}
                  onClick={() => setAsking({ kind: 'delete' })}
                >
                  Delete
                </Button>
              </div>
            </header>

            {asking?.kind === 'duplicate' ? (
              <div className="ask" role="group" aria-label="Duplicate brand">
                <TextField
                  label="Name of the copy"
                  value={asking.name}
                  maxLength={64}
                  onChange={(name) => setAsking({ kind: 'duplicate', name })}
                />
                <Button
                  appearance="accent"
                  disabled={busy || asking.name.trim() === ''}
                  onClick={() =>
                    act(async () => {
                      const copy = await duplicateBrand(current.brand.id, asking.name.trim());
                      await refreshAndSelect(copy.id);
                      return `Created ${copy.name}.`;
                    }, 'The brand could not be duplicated.')
                  }
                >
                  Duplicate
                </Button>
                <Button appearance="outline" onClick={() => setAsking(null)}>
                  Cancel
                </Button>
              </div>
            ) : null}
            {asking?.kind === 'delete' ? (
              <div className="ask" role="alertdialog" aria-label="Delete brand">
                <p>
                  Delete <strong>{current.brand.name}</strong> and its logo files? This cannot be
                  undone.
                </p>
                <Button
                  appearance="accent"
                  disabled={busy}
                  onClick={() =>
                    act(async () => {
                      await deleteBrand(current.brand.id);
                      const list = await listBrands();
                      setBrands(list);
                      select(list, null);
                      setAsking(null);
                      return `Deleted ${current.brand.name}.`;
                    }, 'The brand could not be deleted.')
                  }
                >
                  Delete brand
                </Button>
                <Button appearance="outline" onClick={() => setAsking(null)}>
                  Keep it
                </Button>
              </div>
            ) : null}
            {asking?.kind === 'switch' ? (
              <div className="ask" role="alertdialog" aria-label="Unsaved changes">
                <p>You have unsaved changes. Discard them and open the other brand?</p>
                <Button
                  appearance="accent"
                  onClick={() => {
                    select(brands, asking.id);
                    setAsking(null);
                  }}
                >
                  Discard changes
                </Button>
                <Button appearance="outline" onClick={() => setAsking(null)}>
                  Keep editing
                </Button>
              </div>
            ) : null}

            <TabList tab={tab} onChange={setTab} />
            <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
              {tab === 'colors' ? (
                <>
                  <ColorsPanel data={current.data} onChange={edit} />
                  <SavePalette
                    busy={busy}
                    onSave={(name) =>
                      act(async () => {
                        await createPalette({ name, colors: current.data.colors });
                        onCatalogChange?.();
                        return `Saved the palette "${name}".`;
                      }, 'The palette could not be saved.')
                    }
                  />
                </>
              ) : null}
              {tab === 'fonts' ? (
                <FontsPanel data={current.data} fonts={fonts} onChange={edit} />
              ) : null}
              {tab === 'logo' ? (
                <LogoPanel
                  brand={current.brand}
                  data={current.data}
                  onChange={edit}
                  onStored={onLogoStored}
                  onError={setError}
                />
              ) : null}
              {tab === 'layout' ? (
                <LayoutPanel
                  data={current.data}
                  layouts={layouts}
                  canvases={canvases}
                  onChange={edit}
                />
              ) : null}
            </div>

            {dirty ? (
              <div className="savebar" role="region" aria-label="Unsaved changes">
                <span>You have unsaved changes.</span>
                <Button appearance="accent" disabled={busy} onClick={save}>
                  Save
                </Button>
                <Button appearance="outline" disabled={busy} onClick={discard}>
                  Discard
                </Button>
              </div>
            ) : null}
          </>
        ) : null}
      </section>

      {current ? (
        <Preview
          brand={current.brand}
          data={current.data}
          layout={layoutOf(current)}
          canvas={canvasOf(current)}
        />
      ) : null}
    </div>
  );
}

/** @param {{ tab: string, onChange: (tab: string) => void }} props */
function TabList({ tab, onChange }) {
  function move(/** @type {import('react').KeyboardEvent} */ event) {
    const index = TABS.findIndex(([key]) => key === tab);
    const step = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0;
    if (!step) return;
    event.preventDefault();
    const next = TABS[(index + step + TABS.length) % TABS.length][0];
    onChange(next);
    document.getElementById(`tab-${next}`)?.focus();
  }
  return (
    <div role="tablist" aria-label="Brand settings" className="tabs">
      {TABS.map(([key, label]) => (
        <button
          key={key}
          type="button"
          role="tab"
          id={`tab-${key}`}
          aria-selected={tab === key}
          aria-controls={`panel-${key}`}
          tabIndex={tab === key ? 0 : -1}
          onClick={() => onChange(key)}
          onKeyDown={move}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

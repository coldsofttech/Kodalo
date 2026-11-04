// The four editor panels: Colors, Fonts, Logo and Layout. Each edits a draft of the brand data and
// reports changes up; nothing here talks to Python except the contrast check and logo upload.
import { useEffect, useRef, useState } from 'react';
import { checkContrast, logoUrl, removeLogo, uploadLogo } from '../api.js';
import { COLOR_ROWS, FONT_ROWS, HEX, LOGO_POSITIONS } from '../brand.js';
import { Button, NumberField, Select, TextField } from './controls.jsx';

/** @param {{ value: string, onChange: (value: string) => void, label: string }} props */
function HexField({ value, onChange, label }) {
  const [text, setText] = useState(value);
  const [seen, setSeen] = useState(value);
  if (value !== seen) {
    setSeen(value);
    setText(value);
  }
  const valid = HEX.test(text);
  return (
    <TextField
      label={`${label} (hex)`}
      hideLabel
      value={text}
      maxLength={7}
      invalid={!valid}
      hint={valid ? undefined : 'Use six hex digits, such as #2563eb.'}
      onChange={(next) => {
        setText(next);
        if (HEX.test(next)) onChange(next.toLowerCase());
      }}
    />
  );
}

/** @param {{ name: string, hint: string, pair: { light: string, dark: string }, onChange: (mode: 'light' | 'dark', value: string) => void }} props */
function ColorRow({ name, hint, pair, onChange }) {
  return (
    <fieldset className="color-card">
      <legend>{name}</legend>
      <p className="hint">{hint}</p>
      <div className="color-pair">
        {
          /** @type {const} */ (['light', 'dark']).map((mode) => (
            <div key={mode} className="color-input">
              <span className="mode-caption" aria-hidden="true">
                {mode === 'light' ? 'Light' : 'Dark'}
              </span>
              <div className="color-controls">
                <input
                  type="color"
                  aria-label={`${name}, ${mode} color picker`}
                  value={pair[mode]}
                  onChange={(event) => onChange(mode, event.target.value)}
                />
                <HexField
                  label={`${name}, ${mode}`}
                  value={pair[mode]}
                  onChange={(value) => onChange(mode, value)}
                />
              </div>
            </div>
          ))
        }
      </div>
    </fieldset>
  );
}

/** @param {{ colors: any }} props */
function ContrastReport({ colors }) {
  const [results, setResults] = useState(/** @type {any[] | null} */ (null));
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => {
      checkContrast(colors).then(
        (items) => {
          setFailed(false);
          setResults(items);
        },
        () => setFailed(true),
      );
    }, 250);
    return () => clearTimeout(timer);
  }, [colors]);
  if (failed) return <p className="hint">Contrast could not be checked just now.</p>;
  if (!results) return null;
  const bad = results.filter((item) => !item.passes);
  return (
    <section className="contrast" aria-label="Contrast check">
      <h3>Contrast</h3>
      {bad.length === 0 ? (
        <p role="status">All colors have enough contrast in light and dark.</p>
      ) : (
        <>
          <p role="status">
            {bad.length} {bad.length === 1 ? 'pair needs' : 'pairs need'} more contrast. Your colors
            are never changed for you.
          </p>
          <ul>
            {bad.map((item) => (
              <li key={`${item.color}-${item.mode}`}>
                {item.color} on {item.on}, {item.mode}: {item.ratio}:1 (needs {item.minimum}:1)
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

/** @param {{ data: any, onChange: (path: string, value: unknown) => void }} props */
export function ColorsPanel({ data, onChange }) {
  return (
    <div className="panel">
      <p className="hint">
        Every color has a light and a dark value. The alternative colors are accents used for
        emphasis inside a slide.
      </p>
      <div className="color-grid">
        {COLOR_ROWS.map(([name, key, hint]) => (
          <ColorRow
            key={key}
            name={name}
            hint={hint}
            pair={data.colors[key]}
            onChange={(mode, value) => onChange(`colors.${key}.${mode}`, value)}
          />
        ))}
      </div>
      <ContrastReport colors={data.colors} />
    </div>
  );
}

/** @param {{ data: any, fonts: any[], onChange: (path: string, value: unknown) => void }} props */
export function FontsPanel({ data, fonts, onChange }) {
  const bundled = fonts.filter((font) => font.source === 'bundled');
  const installed = fonts.filter((font) => font.source === 'system');
  return (
    <div className="panel">
      <p className="hint">
        Bundled fonts look the same on every computer. Installed fonts are used if they are
        available where the post is made.
      </p>
      {FONT_ROWS.map(([name, key]) => {
        const current = data.fonts[key];
        const known = fonts.some((font) => font.family === current.family);
        return (
          <Select
            key={key}
            label={name}
            value={current.family}
            onChange={(family) => {
              const match = fonts.find((font) => font.family === family);
              onChange(`fonts.${key}`, { family, source: match?.source ?? 'system' });
            }}
          >
            {known ? null : (
              <option value={current.family}>{current.family} (not installed)</option>
            )}
            <optgroup label="Bundled with Kodalo">
              {bundled.map((font) => (
                <option key={font.family}>{font.family}</option>
              ))}
            </optgroup>
            {installed.length > 0 ? (
              <optgroup label="Installed on this computer">
                {installed.map((font) => (
                  <option key={font.family}>{font.family}</option>
                ))}
              </optgroup>
            ) : null}
          </Select>
        );
      })}
    </div>
  );
}

/**
 * One logo slot: shows the stored file, uploads a new one or removes it. Uploads and removals are
 * saved straight away, since the file lives on the server, not in the draft.
 * @param {{ brand: any, variant: 'light' | 'dark', file: string | null, onStored: (brand: any) => void, onError: (message: string) => void }} props
 */
function LogoSlot({ brand, variant, file, onStored, onError }) {
  const input = useRef(/** @type {HTMLInputElement | null} */ (null));
  const title = variant === 'light' ? 'Logo' : 'Logo for dark mode';
  async function choose(/** @type {File | undefined} */ chosen) {
    if (!chosen) return;
    try {
      onStored(await uploadLogo(brand.id, chosen, variant));
    } catch (error) {
      onError(error instanceof Error ? error.message : 'The logo could not be saved.');
    }
  }
  async function remove() {
    try {
      onStored(await removeLogo(brand.id, variant));
    } catch (error) {
      onError(error instanceof Error ? error.message : 'The logo could not be removed.');
    }
  }
  return (
    <section className="logo-slot" aria-label={title}>
      <h3>{title}</h3>
      {file ? (
        <img
          className="logo-image"
          src={logoUrl(brand.id, variant, brand.updated_at)}
          alt={`${title} of ${brand.name}`}
        />
      ) : (
        <p className="hint">
          {variant === 'light' ? 'No logo yet.' : 'The main logo is used in dark mode.'}
        </p>
      )}
      <div className="row">
        <input
          ref={input}
          type="file"
          accept="image/png,image/svg+xml"
          className="visually-hidden"
          aria-label={`Choose ${title.toLowerCase()} file`}
          onChange={(event) => {
            choose(event.target.files?.[0]);
            event.target.value = '';
          }}
        />
        <Button onClick={() => input.current?.click()}>{file ? 'Replace' : 'Choose file'}</Button>
        {file ? (
          <Button
            appearance="outline"
            danger
            onClick={remove}
            label={`Remove ${title.toLowerCase()}`}
          >
            Remove
          </Button>
        ) : null}
      </div>
    </section>
  );
}

/** @param {{ brand: any, data: any, onChange: (path: string, value: unknown) => void, onStored: (brand: any) => void, onError: (message: string) => void }} props */
export function LogoPanel({ brand, data, onChange, onStored, onError }) {
  const { logo } = data;
  return (
    <div className="panel">
      <p className="hint">
        PNG or SVG, up to 2 MB. Uploading or removing a logo is saved straight away.
      </p>
      <LogoSlot
        brand={brand}
        variant="light"
        file={logo.file}
        onStored={onStored}
        onError={onError}
      />
      <LogoSlot
        brand={brand}
        variant="dark"
        file={logo.dark_file}
        onStored={onStored}
        onError={onError}
      />
      <Select label="Position" value={logo.position} onChange={(v) => onChange('logo.position', v)}>
        {LOGO_POSITIONS.map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </Select>
      <NumberField
        label="Size (percent of width)"
        value={logo.size_percent}
        min={5}
        max={60}
        onChange={(v) => onChange('logo.size_percent', v)}
      />
      <NumberField
        label="Padding (pixels)"
        value={logo.padding}
        min={0}
        max={200}
        onChange={(v) => onChange('logo.padding', v)}
      />
      <Select label="Show on" value={logo.show_on} onChange={(v) => onChange('logo.show_on', v)}>
        <option value="all">All slides</option>
        <option value="first">First slide only</option>
        <option value="last">Last slide only</option>
      </Select>
    </div>
  );
}

/** @param {{ data: any, layouts: any[], canvases: any[], onChange: (path: string, value: unknown) => void }} props */
export function LayoutPanel({ data, layouts, canvases, onChange }) {
  const layout = layouts.find((item) => item.id === data.layout_id);
  const canvas = canvases.find((item) => item.id === layout?.canvas_id);
  return (
    <div className="panel">
      <Select label="Layout" value={data.layout_id} onChange={(id) => onChange('layout_id', id)}>
        {layouts.map((item) => (
          <option key={item.id} value={item.id}>
            {item.name} ({item.slides_count} slides)
          </option>
        ))}
      </Select>
      {layout ? (
        <dl className="summary" aria-label="Layout details">
          <dt>Canvas</dt>
          <dd>
            {canvas ? `${canvas.name} (${canvas.width} x ${canvas.height})` : layout.canvas_id}
          </dd>
          <dt>Slides</dt>
          <dd>{layout.slides_count}</dd>
          <dt>Margins</dt>
          <dd>
            top {layout.margin_top}, sides {layout.margin_side}, bottom {layout.margin_bottom}
          </dd>
          <dt>Corner radius</dt>
          <dd>{layout.corner_radius}</dd>
          <dt>Text</dt>
          <dd>
            {layout.align}, {layout.density}
            {layout.slide_numbers ? ', slide numbers' : ''}
            {layout.footer_text ? `, footer "${layout.footer_text}"` : ''}
          </dd>
        </dl>
      ) : null}
      <p className="hint">
        Layouts are shared by brands. Create and edit them under Brands, Layouts.
      </p>
    </div>
  );
}

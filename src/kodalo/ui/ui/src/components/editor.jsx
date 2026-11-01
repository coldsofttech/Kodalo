// The four editor panels: Colors, Fonts, Logo and Layout. Each edits a draft of the brand data and
// reports changes up; nothing here talks to Python except the contrast check and logo upload.
import { useEffect, useRef, useState } from 'react';
import { checkContrast, logoUrl, removeLogo, uploadLogo } from '../api.js';
import { CANVAS_LABELS, COLOR_ROWS, FONT_ROWS, HEX, LOGO_POSITIONS } from '../brand.js';
import { Button, NumberField, Select, Switch, TextField } from './controls.jsx';

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
          <Button appearance="outline" onClick={remove} label={`Remove ${title.toLowerCase()}`}>
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

/** @param {{ data: any, presets: any[], onChange: (path: string, value: unknown) => void }} props */
export function LayoutPanel({ data, presets, onChange }) {
  const { layout } = data;
  const canvas = layout.canvas;
  function choosePreset(/** @type {string} */ key) {
    const preset = presets.find((item) => item.key === key);
    onChange('layout.canvas', {
      preset: key,
      width: preset ? preset.width : canvas.width,
      height: preset ? preset.height : canvas.height,
    });
  }
  return (
    <div className="panel">
      <Select label="Canvas" value={canvas.preset} onChange={choosePreset}>
        {presets.map((preset) => (
          <option key={preset.key} value={preset.key}>
            {CANVAS_LABELS[/** @type {keyof typeof CANVAS_LABELS} */ (preset.key)] ?? preset.key} (
            {preset.width} x {preset.height})
          </option>
        ))}
        <option value="custom">{CANVAS_LABELS.custom}</option>
      </Select>
      {canvas.preset === 'custom' ? (
        <div className="row">
          <NumberField
            label="Width (pixels)"
            value={canvas.width}
            min={200}
            max={4000}
            onChange={(v) => onChange('layout.canvas.width', v)}
          />
          <NumberField
            label="Height (pixels)"
            value={canvas.height}
            min={200}
            max={4000}
            onChange={(v) => onChange('layout.canvas.height', v)}
          />
        </div>
      ) : null}
      <div className="row">
        <NumberField
          label="Top margin"
          value={layout.margin_top}
          min={0}
          max={400}
          onChange={(v) => onChange('layout.margin_top', v)}
        />
        <NumberField
          label="Side margin"
          value={layout.margin_side}
          min={0}
          max={400}
          onChange={(v) => onChange('layout.margin_side', v)}
        />
        <NumberField
          label="Bottom margin"
          value={layout.margin_bottom}
          min={0}
          max={400}
          onChange={(v) => onChange('layout.margin_bottom', v)}
        />
      </div>
      <NumberField
        label="Corner radius"
        value={layout.corner_radius}
        min={0}
        max={200}
        onChange={(v) => onChange('layout.corner_radius', v)}
      />
      <Select
        label="Text alignment"
        value={layout.align}
        onChange={(v) => onChange('layout.align', v)}
      >
        <option value="left">Left</option>
        <option value="center">Center</option>
      </Select>
      <Select
        label="Spacing"
        value={layout.density}
        onChange={(v) => onChange('layout.density', v)}
      >
        <option value="compact">Compact</option>
        <option value="regular">Regular</option>
        <option value="spacious">Spacious</option>
      </Select>
      <Switch
        label="Show slide numbers"
        checked={layout.slide_numbers}
        onChange={(v) => onChange('layout.slide_numbers', v)}
      />
      <TextField
        label="Footer text"
        value={layout.footer_text}
        maxLength={120}
        hint="Shown at the bottom of every slide, such as a handle or website."
        onChange={(v) => onChange('layout.footer_text', v)}
      />
    </div>
  );
}

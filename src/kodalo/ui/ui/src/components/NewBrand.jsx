import { useState } from 'react';
import { Button, TextField } from './controls.jsx';

/** @param {{ palette: any }} props */
function Swatches({ palette }) {
  const colors = palette.data.colors;
  return (
    <span className="swatches" aria-hidden="true">
      {['background', 'primary', 'secondary', 'text', 'background_alt'].map((key) => (
        <span
          key={key}
          className="swatch"
          data-color={colors[key].light}
          ref={paint(colors[key].light)}
        />
      ))}
    </span>
  );
}

/** Color a swatch through the CSSOM, since inline style attributes are not allowed. */
function paint(/** @type {string} */ color) {
  return (/** @type {HTMLElement | null} */ element) => {
    if (element) element.style.setProperty('background-color', color);
  };
}

/**
 * Choose a starter palette, name the brand and create it.
 * @param {{ palettes: any[], busy: boolean, onCreate: (name: string, palette: string) => void, firstRun?: boolean }} props
 */
export default function NewBrand({ palettes, busy, onCreate, firstRun = false }) {
  const [name, setName] = useState(firstRun ? 'My brand' : '');
  const [palette, setPalette] = useState('midnight');
  const ready = name.trim().length > 0 && !busy;
  return (
    <form
      className="new-brand"
      onSubmit={(event) => {
        event.preventDefault();
        if (ready) onCreate(name.trim(), palette);
      }}
    >
      <fieldset>
        <legend>Start from a palette</legend>
        <div className="palette-cards">
          {palettes.map((item) => (
            <label
              key={item.key}
              className={`palette-card${palette === item.key ? ' selected' : ''}`}
            >
              <input
                type="radio"
                name="palette"
                value={item.key}
                checked={palette === item.key}
                onChange={() => setPalette(item.key)}
              />
              <span className="palette-title">{item.title}</span>
              <Swatches palette={item} />
            </label>
          ))}
        </div>
      </fieldset>
      <TextField label="Brand name" value={name} maxLength={64} onChange={setName} />
      <Button
        appearance="accent"
        disabled={!ready}
        onClick={() => ready && onCreate(name.trim(), palette)}
      >
        Create brand
      </Button>
    </form>
  );
}

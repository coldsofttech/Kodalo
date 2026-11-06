import { useEffect, useState } from 'react';
import { getTheme, saveTheme } from '../../api.js';
import { Button, Select } from '../../components/controls.jsx';
import { setTheme as applyTheme } from '../../theme.js';

const THEME_CHOICES = [
  ['system', 'System (default)'],
  ['light', 'Light'],
  ['dark', 'Dark'],
];

/** The theme the window uses. */
export default function Appearance() {
  const [theme, setTheme] = useState('system');
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    getTheme().then(
      (appearance) => alive && setTheme(appearance.theme),
      (failure) => alive && setError(failure.message),
    );
    return () => {
      alive = false;
    };
  }, []);

  async function save() {
    setBusy(true);
    setError('');
    setSaved(false);
    try {
      const result = await saveTheme(theme);
      applyTheme(result.theme);
      setSaved(true);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Something went wrong.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      className="panel"
      role="tabpanel"
      id="panel-appearance"
      aria-labelledby="tab-appearance"
    >
      <Select label="Theme" value={theme} onChange={setTheme}>
        {THEME_CHOICES.map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </Select>
      <p className="hint">Applies to this window only. System follows Windows.</p>
      <div className="row actions">
        <Button appearance="accent" label="Save" title="Save" disabled={busy} onClick={save}>
          <i className="bi bi-floppy" aria-hidden="true" />
        </Button>
      </div>
      {error ? (
        <p role="alert" className="alert">
          {error}
        </p>
      ) : null}
      {saved ? (
        <p role="status" className="notice">
          Saved.
        </p>
      ) : null}
    </section>
  );
}

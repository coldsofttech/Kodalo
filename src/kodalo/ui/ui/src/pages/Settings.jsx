import { useEffect, useState } from 'react';
import { checkGithub, getGithubSettings, saveGithubSettings } from '../api.js';
import { Button, Select, TextField } from '../components/controls.jsx';

const MODES = [
  ['gh_cli', 'GitHub CLI (gh)'],
  ['local_folder', 'Local folder'],
  ['web_fetch', 'Web fetch'],
];

const HINTS = {
  gh_cli: 'Uses the gh command on this computer. It must be installed and signed in.',
  local_folder: 'Reads repositories you already have in a folder on this computer.',
  web_fetch: 'Reads public repositories over the internet, without signing in.',
};

export default function SettingsPage() {
  const [mode, setMode] = useState('gh_cli');
  const [folder, setFolder] = useState('');
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);
  const [result, setResult] = useState(
    /** @type {{ ok: boolean, detail: string } | null} */ (null),
  );
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    getGithubSettings().then(
      (settings) => {
        if (!alive) return;
        setMode(settings.mode);
        setFolder(settings.local_folder);
      },
      (failure) => alive && setError(failure.message),
    );
    return () => {
      alive = false;
    };
  }, []);

  /** @param {() => Promise<void>} action */
  async function run(action) {
    setBusy(true);
    setError('');
    try {
      await action();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Something went wrong.');
    } finally {
      setBusy(false);
    }
  }

  const save = () =>
    run(async () => {
      setSaved(false);
      setResult(null);
      await saveGithubSettings({ mode, local_folder: folder });
      setSaved(true);
    });

  const test = () =>
    run(async () => {
      setSaved(false);
      setResult(await checkGithub());
    });

  return (
    <section className="card" aria-labelledby="settings-title">
      <h1 id="settings-title">Settings</h1>
      <h2>GitHub connectivity</h2>
      <p>Choose how Kodalo reads your repositories.</p>
      <Select label="Connect with" value={mode} onChange={setMode}>
        {MODES.map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </Select>
      <p className="hint">{HINTS[/** @type {keyof typeof HINTS} */ (mode)]}</p>
      {mode === 'local_folder' ? (
        <TextField label="Folder" value={folder} onChange={setFolder} maxLength={1024} />
      ) : null}
      <Button appearance="accent" disabled={busy} onClick={save}>
        Save
      </Button>
      <Button disabled={busy} onClick={test}>
        Test saved connection
      </Button>
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
      {result ? (
        <p role="status" className={result.ok ? 'notice' : 'alert'}>
          {result.detail}
        </p>
      ) : null}
    </section>
  );
}

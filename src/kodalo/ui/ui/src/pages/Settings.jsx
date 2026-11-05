import { useEffect, useState } from 'react';
import { checkGithub, getGithubSettings, getTheme, saveGithubSettings, saveTheme } from '../api.js';
import { Button, NumberField, Select, TextField } from '../components/controls.jsx';
import { setTheme as applyTheme } from '../theme.js';
import AiConnections from './settings/AiConnections.jsx';
import AiHistory from './settings/AiHistory.jsx';

const TABS = [
  ['github', 'GitHub'],
  ['ai', 'AI Connections'],
  ['ai-history', 'AI History'],
  ['appearance', 'Appearance'],
];

const THEME_CHOICES = [
  ['system', 'System (default)'],
  ['light', 'Light'],
  ['dark', 'Dark'],
];

const MODES = [
  ['gh_cli', 'GitHub CLI (gh)'],
  ['local_folder', 'Local folder'],
  ['web_fetch', 'Web fetch'],
];

const HINTS = new Map([
  ['gh_cli', 'Uses the gh command on this computer. It must be installed and signed in.'],
  ['local_folder', 'Reads repositories you already have in a folder on this computer.'],
  ['web_fetch', 'Reads public repositories over the internet, without signing in.'],
]);

export default function SettingsPage() {
  const [mode, setMode] = useState('gh_cli');
  const [folder, setFolder] = useState('');
  const [manifestLimit, setManifestLimit] = useState(10);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);
  const [result, setResult] = useState(
    /** @type {{ ok: boolean, detail: string } | null} */ (null),
  );
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState('github');
  const [theme, setTheme] = useState('system');
  const [themeSaved, setThemeSaved] = useState(false);

  useEffect(() => {
    let alive = true;
    Promise.all([getGithubSettings(), getTheme()]).then(
      ([settings, appearance]) => {
        if (!alive) return;
        setMode(settings.mode);
        setFolder(settings.local_folder);
        setManifestLimit(settings.manifest_limit);
        setTheme(appearance.theme);
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
      await saveGithubSettings({ mode, local_folder: folder, manifest_limit: manifestLimit });
      setSaved(true);
    });

  const saveAppearance = () =>
    run(async () => {
      setThemeSaved(false);
      const saved = await saveTheme(theme);
      applyTheme(saved.theme);
      setThemeSaved(true);
    });

  const test = () =>
    run(async () => {
      setSaved(false);
      setResult(await checkGithub());
    });

  return (
    <div className="settings">
      <h1>Settings</h1>
      <p>Choose how Kodalo connects to the services it uses.</p>
      <div role="tablist" aria-label="Settings" className="tabs">
        {TABS.map(([key, label]) => (
          <button
            key={key}
            type="button"
            role="tab"
            id={`tab-${key}`}
            aria-selected={tab === key}
            aria-controls={`panel-${key}`}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === 'appearance' ? (
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
            <Button appearance="accent" disabled={busy} onClick={saveAppearance}>
              Save
            </Button>
          </div>
          {error ? (
            <p role="alert" className="alert">
              {error}
            </p>
          ) : null}
          {themeSaved ? (
            <p role="status" className="notice">
              Saved.
            </p>
          ) : null}
        </section>
      ) : null}
      {tab === 'ai' ? (
        <section className="panel" role="tabpanel" id="panel-ai" aria-labelledby="tab-ai">
          <AiConnections />
        </section>
      ) : null}
      {tab === 'ai-history' ? (
        <section
          className="panel"
          role="tabpanel"
          id="panel-ai-history"
          aria-labelledby="tab-ai-history"
        >
          <AiHistory />
        </section>
      ) : null}
      {tab === 'github' ? (
        <section className="panel" role="tabpanel" id="panel-github" aria-labelledby="tab-github">
          <Select label="Connect with" value={mode} onChange={setMode}>
            {MODES.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
          <p className="hint">{HINTS.get(mode)}</p>
          {mode === 'local_folder' ? (
            <TextField label="Folder" value={folder} onChange={setFolder} maxLength={1024} />
          ) : null}
          <NumberField
            label="Project files to read"
            value={manifestLimit}
            min={1}
            max={100}
            onChange={setManifestLimit}
            hint="How many project files (package.json, pyproject.toml ...) are read from a GitHub repository. Each one is a request to GitHub, so a lower number is faster."
          />
          <div className="row actions">
            <Button appearance="accent" disabled={busy} onClick={save}>
              Save
            </Button>
            <Button disabled={busy} onClick={test}>
              Test saved connection
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
          {result ? (
            <p role="status" className={result.ok ? 'notice' : 'alert'}>
              {result.detail}
            </p>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}

import { useEffect, useState } from 'react';
import { checkGithub, getGithubSettings, saveGithubSettings } from '../../libs/api.js';
import { Button, NumberField, Select, TextField } from '../../components/controls.jsx';
import { useSavedValues } from '../../libs/unsaved.js';

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

/** How Kodalo reaches GitHub, and how much it reads from a repository. */
export default function GitHub() {
  const [mode, setMode] = useState('gh_cli');
  const [folder, setFolder] = useState('');
  const [manifestLimit, setManifestLimit] = useState(10);
  const [documentLimit, setDocumentLimit] = useState(10);
  const [documentMaxKb, setDocumentMaxKb] = useState(200);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState('');
  const [result, setResult] = useState(
    /** @type {{ ok: boolean, detail: string } | null} */ (null),
  );
  const [busy, setBusy] = useState(false);
  const markSaved = useSavedValues({
    mode,
    folder,
    manifestLimit,
    documentLimit,
    documentMaxKb,
  });

  useEffect(() => {
    let alive = true;
    getGithubSettings().then(
      (settings) => {
        if (!alive) return;
        setMode(settings.mode);
        setFolder(settings.local_folder);
        setManifestLimit(settings.manifest_limit);
        setDocumentLimit(settings.document_limit);
        setDocumentMaxKb(settings.document_max_kb);
        markSaved({
          mode: settings.mode,
          folder: settings.local_folder,
          manifestLimit: settings.manifest_limit,
          documentLimit: settings.document_limit,
          documentMaxKb: settings.document_max_kb,
        });
      },
      (failure) => alive && setError(failure.message),
    );
    return () => {
      alive = false;
    };
  }, [markSaved]);

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

  /** @param {string} block */
  const save = (block) =>
    run(async () => {
      setSaved('');
      setResult(null);
      await saveGithubSettings({
        mode,
        local_folder: folder,
        manifest_limit: manifestLimit,
        document_limit: documentLimit,
        document_max_kb: documentMaxKb,
      });
      markSaved({ mode, folder, manifestLimit, documentLimit, documentMaxKb });
      setSaved(block);
    });

  const test = () =>
    run(async () => {
      setSaved('');
      setResult(await checkGithub());
    });

  return (
    <>
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
        <div className="row actions">
          <Button
            appearance="accent"
            label="Save connection"
            title="Save connection"
            disabled={busy}
            onClick={() => save('connection')}
          >
            <i className="bi bi-floppy" aria-hidden="true" />
          </Button>
          <Button
            label="Test saved connection"
            title="Test saved connection"
            disabled={busy}
            onClick={test}
          >
            <i className="bi bi-plug" aria-hidden="true" />
          </Button>
        </div>
        {error ? (
          <p role="alert" className="alert">
            {error}
          </p>
        ) : null}
        {saved === 'connection' ? (
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
      <section className="panel" role="tabpanel" aria-label="Reading limits">
        <NumberField
          label="Project files to read"
          value={manifestLimit}
          min={1}
          max={100}
          onChange={setManifestLimit}
          hint="How many project files (package.json, pyproject.toml ...) are read from a GitHub repository. Each one is a request to GitHub, so a lower number is faster."
        />
        <NumberField
          label="Documents to read"
          value={documentLimit}
          min={1}
          max={50}
          onChange={setDocumentLimit}
          hint="How many documents (the README and the docs it links to) are read to find out what a product does."
        />
        <NumberField
          label="Most of each document to read (KB)"
          value={documentMaxKb}
          min={1}
          max={2000}
          onChange={setDocumentMaxKb}
          hint="A longer document is cut off here and a note says so."
        />
        <div className="row actions">
          <Button
            appearance="accent"
            label="Save reading limits"
            title="Save reading limits"
            disabled={busy}
            onClick={() => save('limits')}
          >
            <i className="bi bi-floppy" aria-hidden="true" />
          </Button>
        </div>
        {error ? (
          <p role="alert" className="alert">
            {error}
          </p>
        ) : null}
        {saved === 'limits' ? (
          <p role="status" className="notice">
            Saved.
          </p>
        ) : null}
      </section>
    </>
  );
}

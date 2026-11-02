import { useEffect, useState } from 'react';
import { checkStudioSource, getGithubSettings, readRepository } from '../api.js';
import { Button, Switch, TextField } from '../components/controls.jsx';

const STEPS = [
  ['source', 'Source'],
  ['repository', 'Repository'],
  ['analyze', 'Analyze'],
  ['ideas', 'Ideas'],
  ['post', 'Post'],
];

const MODE_NAMES = new Map([
  ['gh_cli', 'the GitHub CLI'],
  ['local_folder', 'a local folder'],
  ['web_fetch', 'web fetch'],
]);

const EMPTY_DETAILS = {
  owner: '',
  repo: '',
  license: '',
  default_branch: '',
  description: '',
  homepage: '',
  topics: '',
  is_private: false,
  is_fork: false,
  is_archived: false,
};

/** @param {string | null | undefined} value */
const orDash = (value) => (value ? value : '-');

/** @param {{ repo: any, busy: boolean, onRefresh: () => void, onBack: () => void }} props */
function RepositoryView({ repo, busy, onRefresh, onBack }) {
  const facts = [
    ['Address', repo.url],
    ['Description', orDash(repo.description)],
    ['Home page', orDash(repo.homepage)],
    ['Default branch', orDash(repo.default_branch)],
    ['License', orDash(repo.license)],
    ['Topics', orDash(repo.topics.join(', '))],
    ['Private', repo.is_private ? 'Yes' : 'No'],
    ['Fork', repo.is_fork ? 'Yes' : 'No'],
    ['Archived', repo.is_archived ? 'Yes' : 'No'],
    ['Last pushed', orDash(repo.last_pushed_at)],
    ['Files', String(repo.file_count)],
    ['Read with', repo.access_method],
    ['Last read', orDash(repo.last_scanned_at)],
  ];
  return (
    <>
      <h2>
        {repo.owner}/{repo.name}
      </h2>
      <dl className="facts">
        {facts.map(([term, value]) => (
          <div key={term}>
            <dt>{term}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <h3>Languages</h3>
      {repo.languages.length === 0 ? (
        <p className="hint">No languages were found.</p>
      ) : (
        <table className="checks">
          <caption className="visually-hidden">Languages</caption>
          <thead>
            <tr>
              <th scope="col">Language</th>
              <th scope="col">Bytes</th>
              <th scope="col">Share</th>
            </tr>
          </thead>
          <tbody>
            {repo.languages.map((/** @type {any} */ language) => (
              <tr key={language.name}>
                <th scope="row">{language.name}</th>
                <td>{language.bytes}</td>
                <td>{language.percent}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <h3>Top level</h3>
      <ul className="entries">
        {repo.top_level.map((/** @type {any} */ entry) => (
          <li key={entry.path}>
            {entry.path}
            {entry.type === 'dir' ? '/' : ''}
          </li>
        ))}
      </ul>
      {repo.warnings.map((/** @type {string} */ warning) => (
        <p key={warning} role="status" className="hint">
          {warning}
        </p>
      ))}
      <Button appearance="accent" disabled={busy} onClick={onRefresh}>
        Refresh
      </Button>
      <Button disabled={busy} onClick={onBack}>
        Back
      </Button>
    </>
  );
}

/** @param {{ visible: boolean, onOpenSettings: () => void }} props */
export default function StudioPage({ visible, onOpenSettings }) {
  // 'details' is part of the Source step: a folder needs a few answers git cannot give.
  const [step, setStep] = useState('source');
  const [mode, setMode] = useState('gh_cli');
  const [source, setSource] = useState('');
  const [details, setDetails] = useState(EMPTY_DETAILS);
  const [repo, setRepo] = useState(/** @type {any} */ (null));
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  // The mode can change on the Settings page, so read it again whenever this page is shown.
  useEffect(() => {
    if (!visible) return undefined;
    let alive = true;
    getGithubSettings().then(
      (settings) => alive && setMode(settings.mode),
      (failure) => alive && setError(failure.message),
    );
    return () => {
      alive = false;
    };
  }, [visible]);

  const local = mode === 'local_folder';

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

  /** @param {object} [extra] */
  async function read(extra = {}) {
    setRepo(await readRepository({ source, ...extra }));
    setStep('repository');
  }

  const next = () =>
    run(async () => {
      const checked = await checkStudioSource(source);
      if (checked.kind === 'local_folder' && !checked.stored_id) {
        setDetails({ ...EMPTY_DETAILS, ...checked.suggested });
        setStep('details');
        return;
      }
      await read();
    });

  const submitDetails = () =>
    run(() =>
      read({
        details: {
          ...details,
          topics: details.topics
            .split(',')
            .map((topic) => topic.trim())
            .filter(Boolean),
        },
      }),
    );

  /** @param {string} key @param {string | boolean} value */
  const change = (key, value) => setDetails((current) => ({ ...current, [key]: value }));

  const ready = [details.owner, details.repo, details.license, details.default_branch].every(
    (value) => value.trim(),
  );
  const shown = step === 'details' ? 'source' : step;

  return (
    <section className="card" aria-labelledby="studio-title">
      <h1 id="studio-title">Studio</h1>
      <ol className="steps" aria-label="Steps">
        {STEPS.map(([key, label]) => (
          <li key={key} aria-current={shown === key ? 'step' : undefined}>
            {label}
          </li>
        ))}
      </ol>

      {step === 'source' ? (
        <>
          <h2>Choose a repository</h2>
          <p className="hint">
            You connect with {MODE_NAMES.get(mode)}.{' '}
            <button type="button" className="link" onClick={onOpenSettings}>
              Change in Settings
            </button>
          </p>
          <TextField
            label={local ? 'Repository folder' : 'Repository address'}
            hint={
              local ? 'For example C:\\code\\my-app' : 'For example https://github.com/owner/repo'
            }
            value={source}
            onChange={setSource}
            maxLength={1024}
          />
          <Button appearance="accent" disabled={busy || !source.trim()} onClick={next}>
            Next
          </Button>
        </>
      ) : null}

      {step === 'details' ? (
        <>
          <h2>About this repository</h2>
          <p className="hint">
            A folder cannot tell Kodalo everything. Owner, repository name, license and default
            branch are required; the rest is optional.
          </p>
          <TextField label="Owner" value={details.owner} onChange={(v) => change('owner', v)} />
          <TextField
            label="Repository name"
            value={details.repo}
            onChange={(v) => change('repo', v)}
          />
          <TextField
            label="License"
            hint="For example MIT"
            value={details.license}
            onChange={(v) => change('license', v)}
          />
          <TextField
            label="Default branch"
            value={details.default_branch}
            onChange={(v) => change('default_branch', v)}
          />
          <TextField
            label="Description (optional)"
            value={details.description}
            onChange={(v) => change('description', v)}
            maxLength={1024}
          />
          <TextField
            label="Home page (optional)"
            value={details.homepage}
            onChange={(v) => change('homepage', v)}
            maxLength={512}
          />
          <TextField
            label="Topics (optional)"
            hint="Separate with commas"
            value={details.topics}
            onChange={(v) => change('topics', v)}
          />
          <Switch
            label="Private"
            checked={details.is_private}
            onChange={(v) => change('is_private', v)}
          />
          <Switch label="Fork" checked={details.is_fork} onChange={(v) => change('is_fork', v)} />
          <Switch
            label="Archived"
            checked={details.is_archived}
            onChange={(v) => change('is_archived', v)}
          />
          <Button appearance="accent" disabled={busy || !ready} onClick={submitDetails}>
            Continue
          </Button>
          <Button disabled={busy} onClick={() => setStep('source')}>
            Back
          </Button>
        </>
      ) : null}

      {step === 'repository' && repo ? (
        <RepositoryView
          repo={repo}
          busy={busy}
          onRefresh={() => run(() => read({ refresh: true }))}
          onBack={() => setStep('source')}
        />
      ) : null}

      {error ? (
        <p role="alert" className="alert">
          {error}
        </p>
      ) : null}
    </section>
  );
}

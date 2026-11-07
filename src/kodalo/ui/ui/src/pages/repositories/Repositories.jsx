import { useEffect, useState } from 'react';
import {
  addRepository,
  checkRepository,
  getGithubSettings,
  getRepository,
  readReadme,
  listRepositories,
  removeRepository,
} from '../../libs/api.js';
import { Button, Switch, TextField } from '../../components/controls.jsx';
import { localTime } from '../../libs/time.js';
import AiOverlay from '../../components/AiOverlay.jsx';
import SocialPreviewDialog from '../../components/SocialPreviewDialog.jsx';
import ReadmeView from './ReadmeView.jsx';
import RepositoryView from './RepositoryView.jsx';

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

/** @param {{ visible: boolean, onOpenSettings: () => void, onChange?: () => void }} props */
export default function RepositoriesPage({ visible, onOpenSettings, onChange }) {
  const [repos, setRepos] = useState(/** @type {any[]} */ ([]));
  const [mode, setMode] = useState('gh_cli');
  // 'details' follows 'list' for a folder: git cannot give everything the form asks for.
  const [step, setStep] = useState('list');
  const [source, setSource] = useState('');
  const [details, setDetails] = useState(EMPTY_DETAILS);
  const [repo, setRepo] = useState(/** @type {any} */ (null)); // the repository being shown
  const [readme, setReadme] = useState(/** @type {any} */ (null)); // the Analyze step
  const [previewOpen, setPreviewOpen] = useState(false);
  /** What a plain refresh is reading, while it runs; shows the overlay. */
  const [refreshing, setRefreshing] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  // The mode can change on the Settings page, so read everything again whenever this page shows.
  useEffect(() => {
    if (!visible) return undefined;
    let alive = true;
    Promise.all([listRepositories(), getGithubSettings()]).then(
      ([list, settings]) => {
        if (!alive) return;
        setRepos(list);
        setMode(settings.mode);
      },
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
    setMessage('');
    try {
      await action();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Something went wrong.');
    } finally {
      setBusy(false);
    }
  }

  /** @param {object} [extra] */
  async function add(extra = {}) {
    const added = await addRepository({ source, ...extra });
    setRepos(await listRepositories());
    setSource('');
    setDetails(EMPTY_DETAILS);
    setRepo(added);
    setReadme(null);
    setStep('repository');
    onChange?.();
  }

  /** Shows the overlay while `action` runs. @param {() => Promise<void>} action */
  const withOverlay = (action) =>
    run(async () => {
      setRefreshing('Adding the repository…');
      try {
        await action();
      } finally {
        setRefreshing('');
      }
    });

  const next = () =>
    withOverlay(async () => {
      const checked = await checkRepository(source);
      if (checked.kind === 'local_folder' && !checked.stored_id) {
        setDetails({ ...EMPTY_DETAILS, ...checked.suggested });
        setStep('details');
        return;
      }
      await add();
    });

  const submitDetails = () =>
    withOverlay(() =>
      add({
        details: {
          ...details,
          topics: details.topics
            .split(',')
            .map((topic) => topic.trim())
            .filter(Boolean),
        },
      }),
    );

  /** @param {any} item */
  const edit = (item) =>
    run(async () => {
      setRepo(await getRepository(item.id));
      setReadme(null);
      setStep('repository');
    });

  /** Next: read what the README and the docs say (no AI) and show it. */
  const analyze = () =>
    run(async () => {
      setRefreshing('Reading the README and the docs…');
      try {
        setReadme(await readReadme(repo.id, false));
        setStep('analyze');
      } finally {
        setRefreshing('');
      }
    });

  /** Read the README and the docs again. */
  const refreshReadme = () =>
    run(async () => {
      setRefreshing('Reading the README and the docs…');
      try {
        setReadme(await readReadme(repo.id, true));
      } finally {
        setRefreshing('');
      }
    });

  /** Read the shown repository again; the address or folder is what was added. */
  const reread = async () => {
    setRepo(await addRepository({ source: repo.local_path || repo.url, refresh: true }));
    setRepos(await listRepositories());
    onChange?.();
  };

  /** The Refresh button: the same, with the overlay while GitHub is read. */
  const refreshRepo = async () => {
    setRefreshing('Reading the repository…');
    try {
      await reread();
    } finally {
      setRefreshing('');
    }
  };

  /** @param {any} item */
  const remove = (item) =>
    run(async () => {
      await removeRepository(item.id);
      setRepos(await listRepositories());
      setMessage(`Removed ${item.owner}/${item.name}.`);
      onChange?.();
    });

  /** @param {string} key @param {string | boolean} value */
  const change = (key, value) => setDetails((current) => ({ ...current, [key]: value }));

  const ready = [details.owner, details.repo, details.license, details.default_branch].every(
    (value) => value.trim(),
  );

  const showing = (step === 'repository' || step === 'analyze') && repo;

  return (
    <section className="repositories" aria-labelledby="repositories-title">
      {refreshing ? <AiOverlay icon="bi-arrow-repeat" message={refreshing} /> : null}
      {showing ? (
        <>
          <div className="page-head">
            <h1 id="repositories-title">
              {repo.owner}/{repo.name}
            </h1>
            <div className="page-home">
              {repo.has_social_preview ? (
                <Button
                  label="Social preview"
                  title="Social preview"
                  disabled={busy}
                  onClick={() => setPreviewOpen(true)}
                >
                  <i className="bi bi-image" aria-hidden="true" />
                </Button>
              ) : null}
              <Button
                label="Back"
                title="Back"
                disabled={busy || step !== 'analyze'}
                onClick={() => setStep('repository')}
              >
                <i className="bi bi-arrow-left" aria-hidden="true" />
              </Button>
              <Button
                label="Next"
                title="Next"
                disabled={busy || step !== 'repository'}
                onClick={analyze}
              >
                <i className="bi bi-arrow-right" aria-hidden="true" />
              </Button>
              <Button
                className="page-home-end"
                label="Repositories home"
                title="Repositories home"
                disabled={busy}
                onClick={() => setStep('list')}
              >
                <i className="bi bi-house" aria-hidden="true" />
              </Button>
            </div>
          </div>
          {repo.description ? <p className="hint">{repo.description}</p> : null}
        </>
      ) : (
        <>
          <h1 id="repositories-title">Repositories</h1>
          <p className="hint">The repositories your posts are made from.</p>
        </>
      )}

      {step === 'list' ? (
        <>
          <h2>Add a repository</h2>
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
          <div className="row actions">
            <Button
              appearance="accent"
              label="Add"
              title="Add"
              disabled={busy || !source.trim()}
              onClick={next}
            >
              <i className="bi bi-plus-lg" aria-hidden="true" />
            </Button>
          </div>

          <h2 className="section-gap">Your repositories</h2>
          {repos.length === 0 ? (
            <p className="hint">No repositories yet.</p>
          ) : (
            <table className="checks">
              <caption className="visually-hidden">Repositories</caption>
              <thead>
                <tr>
                  <th scope="col">Repository</th>
                  <th scope="col">Branch</th>
                  <th scope="col">License</th>
                  <th scope="col">Last read</th>
                  <th scope="col">
                    <span className="visually-hidden">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {repos.map((item) => (
                  <tr key={item.id}>
                    <th scope="row">
                      <button
                        type="button"
                        className="link"
                        disabled={busy}
                        title="Edit"
                        onClick={() => edit(item)}
                      >
                        {item.owner}/{item.name}
                      </button>
                    </th>
                    <td>{item.default_branch || '-'}</td>
                    <td>{item.license || '-'}</td>
                    <td>{localTime(item.last_scanned_at)}</td>
                    <td className="row-actions">
                      <Button
                        disabled={busy}
                        label={`Edit ${item.owner}/${item.name}`}
                        title="Edit"
                        onClick={() => edit(item)}
                      >
                        <i className="bi bi-pencil" aria-hidden="true" />
                      </Button>{' '}
                      <Button
                        disabled={busy}
                        label={`Remove ${item.owner}/${item.name}`}
                        title="Remove"
                        appearance="outline"
                        danger
                        onClick={() => remove(item)}
                      >
                        <i className="bi bi-trash" aria-hidden="true" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
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
          <div className="row actions">
            <Button
              appearance="accent"
              label="Add"
              title="Add"
              disabled={busy || !ready}
              onClick={submitDetails}
            >
              <i className="bi bi-plus-lg" aria-hidden="true" />
            </Button>
            <Button disabled={busy} onClick={() => setStep('list')}>
              <i className="bi bi-arrow-left" aria-hidden="true" /> Back
            </Button>
          </div>
        </>
      ) : null}

      {previewOpen && repo ? (
        <SocialPreviewDialog repo={repo} onClose={() => setPreviewOpen(false)} />
      ) : null}

      {step === 'repository' && repo ? (
        <RepositoryView
          repo={repo}
          busy={busy}
          onRefresh={() => run(refreshRepo)}
          onReload={reread}
          onRun={run}
        />
      ) : null}

      {step === 'analyze' && repo && readme ? (
        <ReadmeView
          repo={repo}
          readme={readme}
          busy={busy}
          onRun={run}
          onChange={setReadme}
          onRefresh={refreshReadme}
        />
      ) : null}

      {message ? (
        <p role="status" className="hint">
          {message}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="alert">
          {error}
        </p>
      ) : null}
    </section>
  );
}

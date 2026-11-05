import { useEffect, useState } from 'react';
import {
  checkStudioSource,
  getGithubSettings,
  openExternal,
  planAnalysis,
  readRepository,
  runAnalysis,
} from '../api.js';
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

/** The documentation files that were found, as names (the docs folder ends with a slash). */
function documentationNames(/** @type {any} */ docs) {
  if (!docs) return [];
  return [
    ...docs.readmes,
    docs.changelog,
    docs.contributing,
    docs.license_file,
    docs.code_of_conduct,
    docs.security,
    docs.docs_dir ? `${docs.docs_dir}/` : '',
  ].filter(Boolean);
}

/** A web address as a link that opens in the system's browser; other text is shown as it is. */
function webLink(/** @type {string | null | undefined} */ url) {
  if (!url) return '-';
  if (!/^https?:\/\//i.test(url)) return url;
  return (
    <a
      href={url}
      onClick={(event) => {
        event.preventDefault();
        openExternal(url);
      }}
    >
      {url}
    </a>
  );
}

/** A timestamp in the user's own time zone and format; the text itself if it is not a date. */
function localTime(/** @type {string | null | undefined} */ value) {
  if (!value) return '-';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

/** @param {{ repo: any, busy: boolean, onRefresh: () => void, onBack: () => void }} props */
function packageText(/** @type {any} */ manifest) {
  if (manifest.is_lockfile) return 'Lockfile';
  if (!manifest.package_name) return orDash('');
  return manifest.version ? `${manifest.package_name} ${manifest.version}` : manifest.package_name;
}

function Dependencies(/** @type {{ manifest: any }} */ { manifest }) {
  const all = [
    ...manifest.dependencies.map((/** @type {string} */ name) => ({ name, dev: false })),
    ...manifest.dev_dependencies.map((/** @type {string} */ name) => ({ name, dev: true })),
  ];
  if (all.length === 0) return orDash('');
  const dev = manifest.dev_dependencies.length;
  return (
    <details>
      <summary>
        {manifest.dependencies.length} {dev > 0 ? `(+${dev} dev)` : ''}
      </summary>
      <ul className="topics" aria-label={`Dependencies of ${manifest.path}`}>
        {all.map((item) => (
          <li key={`${item.dev}-${item.name}`} className="topic">
            {item.name}
            {item.dev ? ' (dev)' : ''}
          </li>
        ))}
      </ul>
    </details>
  );
}

/** Whether an analysis plan has anything to send: project files, package names or tooling names. */
function hasWork(/** @type {any} */ plan) {
  return plan.files.length > 0 || plan.dependencies.length > 0 || plan.tool_files.length > 0;
}

function AiStep(
  /** @type {{ repo: any, busy: boolean, onRun: (action: () => Promise<void>) => void, onDone: () => Promise<void>, onRefresh: () => void, onBack: () => void }} */ {
    repo,
    busy,
    onRefresh,
    onBack,
    onRun,
    onDone,
  },
) {
  const [plan, setPlan] = useState(/** @type {any} */ (null));
  const [message, setMessage] = useState('');

  const ask = () =>
    onRun(async () => {
      setMessage('');
      const next = await planAnalysis(repo.id);
      if (!hasWork(next)) {
        setMessage('Everything is already understood, so there is nothing to ask the AI.');
        return;
      }
      setPlan(next);
    });

  const proceed = () =>
    onRun(async () => {
      setPlan(null);
      const result = await runAnalysis(repo.id);
      const saved = result.parsers.length + result.frameworks.length + result.tools.length;
      setMessage(
        [
          `Saved ${result.parsers.length} parser(s), ${result.frameworks.length} framework(s) and ${result.tools.length} tool(s).`,
          ...result.skipped,
        ].join(' '),
      );
      if (saved > 0) await onDone();
    });

  return (
    <>
      <div className="row actions">
        <Button appearance="accent" disabled={busy} onClick={onRefresh}>
          Refresh
        </Button>
        <Button disabled={busy || plan !== null} onClick={ask}>
          Refresh with AI
        </Button>
        <Button disabled={busy} onClick={onBack}>
          Back
        </Button>
      </div>
      {plan ? (
        <div role="group" aria-labelledby="ai-plan-title" className="confirm">
          <h3 id="ai-plan-title">Send to {plan.label}?</h3>
          {plan.files.length > 0 ? (
            <p>
              Kodalo will send the start of {plan.files.join(', ')} to write parser settings. Lines
              that look like secrets are removed first.
            </p>
          ) : null}
          {plan.dependencies.length > 0 || plan.tool_files.length > 0 ? (
            <>
              <p>
                Kodalo will send these names, never file contents, to find out which are frameworks
                and tools.
              </p>
              <p>Package names: {plan.dependencies.join(', ') || 'none'}.</p>
              <p>
                Top-level file names: {[...new Set([...plan.names, ...plan.tool_files])].join(', ')}
                .
              </p>
            </>
          ) : null}
          <p>
            Everything goes to {plan.label} ({plan.model}). About {plan.input_tokens} tokens sent,
            and at most {plan.max_output_tokens} tokens in the answer.
          </p>
          <div className="row actions">
            <Button appearance="accent" disabled={busy} onClick={proceed}>
              Proceed
            </Button>
            <Button disabled={busy} onClick={() => setPlan(null)}>
              Cancel
            </Button>
          </div>
        </div>
      ) : null}
      {message ? (
        <p role="status" className="hint">
          {message}
        </p>
      ) : null}
    </>
  );
}

function RepositoryView({ repo, busy, onRefresh, onReload, onBack, onRun }) {
  const facts = [
    ['Address', webLink(repo.url)],
    ['Description', orDash(repo.description)],
    ['Home page', webLink(repo.homepage)],
    ['Default branch', orDash(repo.default_branch)],
    ['License', orDash(repo.license)],
    [
      'Topics',
      repo.topics.length ? (
        <ul className="topics" aria-label="Topics">
          {repo.topics.map((/** @type {string} */ topic) => (
            <li key={topic} className="topic">
              {topic}
            </li>
          ))}
        </ul>
      ) : (
        orDash('')
      ),
    ],
    ['Private', repo.is_private ? 'Yes' : 'No'],
    ['Fork', repo.is_fork ? 'Yes' : 'No'],
    ['Archived', repo.is_archived ? 'Yes' : 'No'],
    ['Last pushed', localTime(repo.last_pushed_at)],
    ['Files', String(repo.file_count)],
    ['Monorepo', repo.is_monorepo ? `Yes (${repo.monorepo_signals.join(', ')})` : 'No'],
    ['Documentation', orDash(documentationNames(repo.documentation).join(', '))],
    [
      'Not read',
      orDash(
        (repo.skipped ?? []).map((/** @type {any} */ s) => `${s.path} (${s.reason})`).join(', '),
      ),
    ],
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
          <li key={entry.path} className={entry.type === 'dir' ? 'folder' : 'file'}>
            <span aria-hidden="true" className="entry-icon">
              {entry.type === 'dir' ? '📁' : '📄'}
            </span>
            {entry.path}
            {entry.type === 'dir' ? '/' : ''}
          </li>
        ))}
      </ul>
      <h3>Notable folders</h3>
      {repo.notable_dirs.length === 0 ? (
        <p className="hint">No notable folders were found.</p>
      ) : (
        <table className="checks">
          <caption className="visually-hidden">Notable folders</caption>
          <thead>
            <tr>
              <th scope="col">Folder</th>
              <th scope="col">Used for</th>
            </tr>
          </thead>
          <tbody>
            {repo.notable_dirs.map((/** @type {any} */ dir) => (
              <tr key={dir.path}>
                <th scope="row">
                  <span aria-hidden="true" className="entry-icon">
                    📁
                  </span>
                  {dir.path}/
                </th>
                <td>
                  <span className="topic">{dir.purpose}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <h3>Frameworks</h3>
      {repo.frameworks.length === 0 ? (
        <p className="hint">No frameworks were recognised.</p>
      ) : (
        <table className="checks">
          <caption className="visually-hidden">Frameworks</caption>
          <thead>
            <tr>
              <th scope="col">Framework</th>
              <th scope="col">Category</th>
              <th scope="col">Found in</th>
            </tr>
          </thead>
          <tbody>
            {repo.frameworks.map((/** @type {any} */ framework) => (
              <tr key={framework.id}>
                <th scope="row">{framework.name}</th>
                <td>
                  <span className="topic">{framework.category}</span>
                </td>
                <td>{framework.evidence}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <h3>Tooling</h3>
      {repo.tooling.length === 0 ? (
        <p className="hint">
          No build, test, lint, CI, container or package tools were recognised.
        </p>
      ) : (
        <table className="checks">
          <caption className="visually-hidden">Tooling</caption>
          <thead>
            <tr>
              <th scope="col">Tool</th>
              <th scope="col">Category</th>
              <th scope="col">Found in</th>
            </tr>
          </thead>
          <tbody>
            {repo.tooling.map((/** @type {any} */ tool) => (
              <tr key={tool.id}>
                <th scope="row">{tool.name}</th>
                <td>
                  <span className="topic">{tool.category}</span>
                </td>
                <td>{tool.evidence}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <h3>Project files</h3>
      {repo.manifests.length === 0 ? (
        <p className="hint">No project files were found.</p>
      ) : (
        <table className="checks">
          <caption className="visually-hidden">Project files</caption>
          <thead>
            <tr>
              <th scope="col">File</th>
              <th scope="col">Ecosystem</th>
              <th scope="col">Package</th>
              <th scope="col">Dependencies</th>
              <th scope="col">Evidence</th>
            </tr>
          </thead>
          <tbody>
            {repo.manifests.map((/** @type {any} */ manifest) => (
              <tr key={manifest.path}>
                <th scope="row">
                  <span aria-hidden="true" className="entry-icon">
                    📄
                  </span>
                  {manifest.path}
                </th>
                <td>
                  <span className="topic">{manifest.ecosystem}</span>
                </td>
                <td>{packageText(manifest)}</td>
                <td>
                  <Dependencies manifest={manifest} />
                </td>
                <td>{orDash(manifest.evidence)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {repo.warnings.map((/** @type {string} */ warning) => (
        <p key={warning} role="status" className="hint">
          {warning}
        </p>
      ))}
      <AiStep
        repo={repo}
        busy={busy}
        onRefresh={onRefresh}
        onBack={onBack}
        onRun={onRun}
        onDone={onReload}
      />
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
    <section className="studio" aria-labelledby="studio-title">
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
          <div className="row actions">
            <Button appearance="accent" disabled={busy || !source.trim()} onClick={next}>
              Next
            </Button>
          </div>
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
            <Button appearance="accent" disabled={busy || !ready} onClick={submitDetails}>
              Continue
            </Button>
            <Button disabled={busy} onClick={() => setStep('source')}>
              Back
            </Button>
          </div>
        </>
      ) : null}

      {step === 'repository' && repo ? (
        <RepositoryView
          repo={repo}
          busy={busy}
          onRefresh={() => run(() => read({ refresh: true }))}
          onReload={() => read({ refresh: true })}
          onBack={() => setStep('source')}
          onRun={run}
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

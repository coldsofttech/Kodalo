import { useState } from 'react';
import { openExternal, planAnalysis, runAnalysis } from '../../api.js';
import AiOverlay from '../../components/AiOverlay.jsx';
import Section from '../../components/Section.jsx';
import { Button } from '../../components/controls.jsx';
import { languageColor } from '../../languageColors.js';
import { localTime } from '../../time.js';

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

/** @param {number} percent */
const percentText = (percent) => `${Number(percent.toFixed(1))}%`;

/** Bootstrap icon classes for a file, by extension. */
const FILE_ICONS = new Map([
  ['md', 'bi-markdown'],
  ['json', 'bi-filetype-json'],
  ['yml', 'bi-filetype-yml'],
  ['yaml', 'bi-filetype-yml'],
  ['py', 'bi-filetype-py'],
  ['js', 'bi-filetype-js'],
  ['html', 'bi-filetype-html'],
  ['css', 'bi-filetype-css'],
  ['sh', 'bi-filetype-sh'],
  ['txt', 'bi-filetype-txt'],
  ['lock', 'bi-lock'],
  ['toml', 'bi-file-earmark-code'],
]);

/** @param {string} path */
const fileIcon = (path) =>
  FILE_ICONS.get(path.split('.').at(-1)?.toLowerCase() ?? '') ?? 'bi-file-earmark';

/** A folder or file icon in front of a name. */
function EntryIcon(/** @type {{ dir?: boolean, path?: string }} */ { dir, path = '' }) {
  return (
    <i
      className={`bi ${dir ? 'bi-folder-fill folder-icon' : fileIcon(path)} entry-icon`}
      aria-hidden="true"
    />
  );
}

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
  /** @type {{ repo: any, busy: boolean, onRun: (action: () => Promise<void>) => void, onDone: () => Promise<void>, onRefresh: () => void }} */ {
    repo,
    busy,
    onRefresh,
    onRun,
    onDone,
  },
) {
  const [plan, setPlan] = useState(/** @type {any} */ (null));
  const [message, setMessage] = useState('');
  /** True while the AI works, to show the overlay. */
  const [thinking, setThinking] = useState(false);

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
      setThinking(true);
      let result;
      try {
        result = await runAnalysis(repo.id);
      } finally {
        setThinking(false);
      }
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
      {thinking ? <AiOverlay message="The AI is reading the repository…" /> : null}
      <div className="row actions repo-actions">
        <Button
          appearance="accent"
          label="Refresh"
          title="Refresh"
          disabled={busy}
          onClick={onRefresh}
        >
          <i className="bi bi-arrow-repeat" aria-hidden="true" />
        </Button>
        <Button
          className="ai-button"
          label="Refresh with AI"
          title="Refresh with AI"
          disabled={busy || plan !== null}
          onClick={ask}
        >
          <i className="bi bi-stars" aria-hidden="true" />
        </Button>
      </div>
      {plan ? (
        <div role="group" aria-labelledby="ai-plan-title" className="confirm">
          <h2 id="ai-plan-title">Send to {plan.label}?</h2>
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
            <Button
              appearance="accent"
              label="Proceed"
              title="Proceed"
              disabled={busy}
              onClick={proceed}
            >
              <i className="bi bi-check-lg" aria-hidden="true" />
            </Button>
            <Button label="Cancel" title="Cancel" disabled={busy} onClick={() => setPlan(null)}>
              <i className="bi bi-x-lg" aria-hidden="true" />
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

/** @param {{ repo: any, busy: boolean, onRefresh: () => void, onReload: () => Promise<void>, onRun: (action: () => Promise<void>) => void }} props */
export default function RepositoryView({ repo, busy, onRefresh, onReload, onRun }) {
  const facts = [
    ['Address', webLink(repo.url)],
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
    [
      'Properties',
      <ul key="flags" className="flags">
        {[
          ['Private', 'bi-lock', repo.is_private, ''],
          ['Fork', 'bi-diagram-2', repo.is_fork, ''],
          ['Archived', 'bi-archive', repo.is_archived, ''],
          ['Monorepo', 'bi-boxes', repo.is_monorepo, repo.monorepo_signals.join(', ')],
        ].map(([name, icon, on, detail]) => (
          <li key={name} className={on ? 'flag on' : 'flag'} title={detail || undefined}>
            <i className={`bi ${icon}`} aria-hidden="true" /> {name}: {on ? 'Yes' : 'No'}
          </li>
        ))}
      </ul>,
    ],
    [
      'Activity',
      <ul key="activity" className="flags">
        <li className="flag on">
          <i className="bi bi-clock-history" aria-hidden="true" /> Last pushed:{' '}
          {localTime(repo.last_pushed_at)}
        </li>
        <li className="flag on">
          <i className="bi bi-files" aria-hidden="true" /> Files: {repo.file_count}
        </li>
      </ul>,
    ],
    [
      'Documentation',
      documentationNames(repo.documentation).length ? (
        <ul className="topics" aria-label="Documentation">
          {documentationNames(repo.documentation).map((/** @type {string} */ name) => (
            <li key={name} className="topic">
              {name}
            </li>
          ))}
        </ul>
      ) : (
        orDash('')
      ),
    ],
    ...((repo.skipped ?? []).length > 0
      ? [
          [
            'Not read',
            (repo.skipped ?? [])
              .map((/** @type {any} */ s) => `${s.path} (${s.reason})`)
              .join(', '),
          ],
        ]
      : []),
    [
      'Source',
      <ul key="source" className="flags">
        <li className="flag on">
          <i className="bi bi-download" aria-hidden="true" /> Read with: {repo.access_method}
        </li>
        <li className="flag on">
          <i className="bi bi-arrow-repeat" aria-hidden="true" /> Last read:{' '}
          {localTime(repo.last_scanned_at)}
        </li>
      </ul>,
    ],
  ];
  return (
    <>
      <dl className="facts">
        {facts.map(([term, value]) => (
          <div key={term}>
            <dt>{term}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <h2>Languages</h2>
      {repo.languages.length === 0 ? (
        <p className="hint">No languages were found.</p>
      ) : (
        <>
          {/* A plain SVG, since the content security policy forbids style attributes. */}
          <div className="language-bar">
            <svg
              viewBox="0 0 100 1"
              preserveAspectRatio="none"
              role="img"
              aria-label={repo.languages
                .map((/** @type {any} */ l) => `${l.name} ${percentText(l.percent)}`)
                .join(', ')}
            >
              {repo.languages.map((/** @type {any} */ language, /** @type {number} */ index) => (
                <rect
                  key={language.name}
                  x={repo.languages
                    .slice(0, index)
                    .reduce(
                      (/** @type {number} */ sum, /** @type {any} */ l) => sum + l.percent,
                      0,
                    )}
                  width={language.percent}
                  height="1"
                  fill={languageColor(language.name)}
                />
              ))}
            </svg>
          </div>
          <ul className="language-legend">
            {repo.languages.map((/** @type {any} */ language) => (
              <li key={language.name}>
                <svg viewBox="0 0 1 1" className="language-dot" aria-hidden="true">
                  <circle cx="0.5" cy="0.5" r="0.5" fill={languageColor(language.name)} />
                </svg>
                <strong>{language.name}</strong> <span>{percentText(language.percent)}</span>
              </li>
            ))}
          </ul>
        </>
      )}
      <Section title="Top level" icon="bi-diagram-3" count={repo.top_level.length}>
        <ul className="entries">
          {repo.top_level.map((/** @type {any} */ entry) => (
            <li key={entry.path} className={entry.type === 'dir' ? 'folder' : 'file'}>
              <EntryIcon dir={entry.type === 'dir'} path={entry.path} />
              {entry.path}
              {entry.type === 'dir' ? '/' : ''}
            </li>
          ))}
        </ul>
      </Section>
      <Section
        title="Notable folders"
        icon="bi-folder-symlink-fill"
        count={repo.notable_dirs.length}
      >
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
                    <EntryIcon dir />
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
      </Section>
      <Section title="Frameworks" icon="bi-puzzle" count={repo.frameworks.length}>
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
      </Section>
      <Section title="Tooling" icon="bi-tools" count={repo.tooling.length}>
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
      </Section>
      <Section title="Project files" icon="bi-file-earmark-code" count={repo.manifests.length}>
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
                    <EntryIcon path={manifest.path} />
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
      </Section>
      {repo.warnings.map((/** @type {string} */ warning) => (
        <p key={warning} role="status" className="hint">
          {warning}
        </p>
      ))}
      <AiStep repo={repo} busy={busy} onRefresh={onRefresh} onRun={onRun} onDone={onReload} />
    </>
  );
}

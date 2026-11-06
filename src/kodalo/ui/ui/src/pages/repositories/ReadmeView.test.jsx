import { afterEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ReadmeView from './ReadmeView.jsx';
import { makeRepo, mockApi } from '../../testing.js';

afterEach(() => vi.unstubAllGlobals());

const evidence = (/** @type {string} */ file) => ({ file, quote: 'q', status: 'documented' });

const README = {
  repository_id: 'r1',
  tagline: 'Repo cleans things.',
  summary: 'Repo cleans things. It is fast.',
  purpose_file: 'README.md',
  installation: [
    { method: 'pip', command: 'pip install repo', note: '', evidence: evidence('README.md') },
  ],
  capabilities: [
    {
      name: 'Clean caches',
      description: 'remove caches',
      note: '',
      evidence: evidence('docs/cli.md'),
    },
    { name: 'Service', description: '', note: 'Planned', evidence: evidence('README.md') },
  ],
  features: [
    {
      name: 'Safe cleanup',
      description: 'Only removes ignored files.',
      importance: 'headline',
      maturity: 'stable',
      claims: [{ type: 'absolute', text: 'Never deletes tracked files', reason: '' }],
      use_cases: ['Free disk space'],
      evidence: evidence('README.md'),
    },
    {
      name: 'Hooks',
      description: '',
      importance: 'minor',
      maturity: 'unspecified',
      claims: [],
      use_cases: [],
      evidence: evidence('README.md'),
    },
  ],
  use_cases: [
    { title: 'Free disk space', description: 'Clean caches.', evidence: evidence('README.md') },
  ],
  documents: [{ path: 'SECURITY.md', status: 'skipped', reason: 'not about the product', size: 0 }],
  warnings: [],
  analyzed_at: 'now',
  use_cases_at: null,
};
const EMPTY = {
  ...README,
  tagline: '',
  summary: '',
  installation: [],
  capabilities: [],
  features: [],
  use_cases: [],
};
const PLAN = {
  provider: 'claude_api',
  label: 'Claude API',
  model: 'claude-haiku-5-5',
  documents: ['README.md', 'docs/cli.md'],
  input_tokens: 400,
  max_output_tokens: 900,
};
const DONE = {
  installation: 1,
  capabilities: 2,
  features: 0,
  use_cases: 1,
  skipped: ['Left out one.'],
  input_tokens: 400,
  output_tokens: 90,
};

/** @param {any} [readme] @param {Partial<Record<string, any>>} [props] */
function show(readme = README, props = {}) {
  const handlers = {
    onChange: vi.fn(),
    onRefresh: vi.fn(),
    onRun: vi.fn((/** @type {() => Promise<void>} */ action) => action()),
  };
  const view = render(
    <ReadmeView repo={makeRepo('o')} readme={readme} busy={false} {...handlers} {...props} />,
  );
  return { ...view, ...handlers };
}

/** @param {string} title */
const section = (title) =>
  /** @type {HTMLElement} */ (
    screen.getByText(title, { selector: '.accordion-title' }).closest('details')
  );

describe('ReadmeView', () => {
  it('shows every part as a closed section with a count, and no documents list', async () => {
    const { container } = show();

    for (const title of ['Purpose', 'Installation', 'Capabilities', 'Features', 'Use cases']) {
      expect(section(title)).not.toHaveAttribute('open');
    }
    expect(section('Installation')).toHaveTextContent('1');
    expect(section('Capabilities')).toHaveTextContent('2');
    expect(section('Features')).toHaveTextContent('2');
    expect(screen.queryByText('SECURITY.md')).not.toBeInTheDocument();
    expect(screen.queryByText('Documents')).not.toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('shows the purpose as the summary only, falling back to the tagline', () => {
    const { unmount } = show();
    expect(screen.getByText('Repo cleans things. It is fast.')).toBeInTheDocument();
    expect(screen.queryByText('Repo cleans things.')).not.toBeInTheDocument();
    unmount();

    show({ ...README, summary: '' });
    expect(screen.getByText('Repo cleans things.')).toBeInTheDocument();
  });

  it('shows where each installation method and capability was found as a badge', () => {
    show();

    expect(screen.getByRole('row', { name: 'pip pip install repo README.md' })).toBeInTheDocument();
    const row = screen.getByRole('row', { name: /Clean caches remove caches docs\/cli.md/ });
    expect(row).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Command' })).toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: 'Found in' })).not.toBeInTheDocument();
    expect(screen.getByText('Planned')).toHaveClass('topic');
  });

  it('shows features with their badges and the claims to repeat with care', () => {
    show();

    const row = screen.getByRole('row', { name: /Safe cleanup.*headline.*stable/ });
    expect(row).toHaveTextContent('Only removes ignored files.');
    expect(row).toHaveTextContent('Used in: Free disk space.');
    expect(row).toHaveTextContent('Repeat with care: Never deletes tracked files.');
    const plain = screen.getByRole('row', { name: /Hooks.*minor/ });
    expect(plain).not.toHaveTextContent('unspecified');
    expect(plain).not.toHaveTextContent('Used in');
  });

  it('shows the use cases in a table', () => {
    show();

    expect(screen.getByRole('row', { name: 'Free disk space Clean caches.' })).toBeInTheDocument();
  });

  it('says what to do when a part is empty', () => {
    show(EMPTY);

    expect(screen.getByText('No introduction was found in the documents.')).toBeInTheDocument();
    expect(
      screen.getByText('No way to install it was found in the documents.'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('No features or commands were listed in the documents.'),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Features group the capabilities, so the AI writes them/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Use cases need judgement, so the AI writes them/)).toBeInTheDocument();
  });

  it('shows the warnings', () => {
    show({ ...README, warnings: ['README.md is larger than 200 KB.'] });

    expect(screen.getByText('README.md is larger than 200 KB.')).toBeInTheDocument();
  });

  it('asks the parent to refresh, and disables the buttons while busy', async () => {
    const { onRefresh, unmount } = show();
    await userEvent.click(screen.getByLabelText('Refresh'));
    expect(onRefresh).toHaveBeenCalledOnce();
    unmount();

    show(README, { busy: true });
    expect(screen.getByLabelText('Refresh')).toHaveAttribute('disabled');
    expect(screen.getByLabelText('Refresh with AI')).toHaveAttribute('disabled');
  });

  it('shows what would be sent, sends nothing until Proceed, then shows the new analysis', async () => {
    const better = { ...README, summary: 'Better summary.' };
    const calls = mockApi((_method, path) => {
      if (path.endsWith('/readme/analysis/plan')) return PLAN;
      if (path.endsWith('/readme/analysis')) return DONE;
      if (path.endsWith('/readme')) return better;
      return undefined;
    });
    const { container, onChange } = show();

    await userEvent.click(screen.getByLabelText('Refresh with AI'));
    expect(await screen.findByText(/About 400 tokens sent/)).toBeInTheDocument();
    expect(screen.getByText(/README.md, docs\/cli.md/)).toBeInTheDocument();
    expect(calls.some((call) => call.path.endsWith('/readme/analysis'))).toBe(false);
    expect(await axe(container)).toHaveNoViolations();

    await userEvent.click(screen.getByLabelText('Proceed'));
    expect(
      await screen.findByText(
        /Saved 1 installation method\(s\), 2 capabilities, 0 feature\(s\) and 1 use case\(s\)\./,
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/Left out one\./)).toBeInTheDocument();
    expect(calls.filter((call) => call.path.endsWith('/readme/analysis')).length).toBe(1);
    expect(onChange).toHaveBeenCalledWith(better);
    expect(screen.queryByLabelText('Proceed')).not.toBeInTheDocument();
  });

  it('shows the work in progress while the AI answers', async () => {
    /** @type {(value: Response) => void} */
    let finish = () => undefined;
    vi.stubGlobal(
      'fetch',
      vi.fn(async (/** @type {string} */ path) => {
        if (path.endsWith('/analysis/plan'))
          return { ok: true, status: 200, json: async () => PLAN };
        if (path.endsWith('/analysis')) {
          return new Promise((resolve) => {
            finish = resolve;
          });
        }
        return { ok: true, status: 200, json: async () => README };
      }),
    );
    show();

    await userEvent.click(screen.getByLabelText('Refresh with AI'));
    await userEvent.click(await screen.findByLabelText('Proceed'));
    expect(await screen.findByText('The AI is reading the documents…')).toBeInTheDocument();

    finish(/** @type {any} */ ({ ok: true, status: 200, json: async () => DONE }));
    await screen.findByText(/Saved 1 installation/);
    expect(screen.queryByText('The AI is reading the documents…')).not.toBeInTheDocument();
  });

  it('cancels the AI question without sending anything', async () => {
    const calls = mockApi((_method, path) =>
      path.endsWith('/readme/analysis/plan') ? PLAN : undefined,
    );
    show();

    await userEvent.click(screen.getByLabelText('Refresh with AI'));
    await userEvent.click(await screen.findByLabelText('Cancel'));

    expect(screen.queryByLabelText('Proceed')).not.toBeInTheDocument();
    expect(calls.some((call) => call.path.endsWith('/readme/analysis'))).toBe(false);
  });

  it('says so when there is no document to send', async () => {
    mockApi((_method, path) =>
      path.endsWith('/readme/analysis/plan') ? { ...PLAN, documents: [] } : undefined,
    );
    show();

    await userEvent.click(screen.getByLabelText('Refresh with AI'));

    expect(await screen.findByText(/so there is nothing to send/)).toBeInTheDocument();
    expect(screen.queryByLabelText('Proceed')).not.toBeInTheDocument();
  });
});

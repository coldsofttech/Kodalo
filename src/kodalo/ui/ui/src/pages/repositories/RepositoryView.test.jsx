import { afterEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import RepositoryView from './RepositoryView.jsx';
import { makeRepo, mockApi } from '../../testing.js';

afterEach(() => vi.unstubAllGlobals());

/** @param {any} [repo] @param {Partial<Record<string, any>>} [props] */
function show(repo = makeRepo('o'), props = {}) {
  const handlers = {
    onRefresh: vi.fn(),
    onReload: vi.fn(async () => undefined),
    onRun: vi.fn((/** @type {() => Promise<void>} */ action) => action()),
  };
  const view = render(<RepositoryView repo={repo} busy={false} {...handlers} {...props} />);
  return { ...view, ...handlers };
}

const PLAN = {
  provider: 'claude_api',
  label: 'Claude API',
  model: 'claude-haiku-5-5',
  files: ['Gemfile'],
  dependencies: ['htmx'],
  names: ['src'],
  tool_files: ['Earthfile'],
  input_tokens: 1300,
  max_output_tokens: 3100,
};
const NO_WORK = { ...PLAN, files: [], dependencies: [], names: [], tool_files: [] };
const DONE = {
  parsers: ['ruby-gemfile'],
  frameworks: ['htmx'],
  tools: ['earthly'],
  skipped: ['Skipped one.'],
  input_tokens: 1230,
  output_tokens: 390,
};

describe('RepositoryView', () => {
  it('shows the facts, flags and tags of the repository', async () => {
    const { container } = show();

    expect(screen.getByText('https://github.com/o/repo')).toBeInTheDocument();
    expect(screen.getByText('main')).toBeInTheDocument();
    expect(screen.getByText('MIT')).toBeInTheDocument();
    expect(within(screen.getByRole('list', { name: 'Topics' })).getByText('cli')).toBeVisible();
    expect(
      within(screen.getByRole('list', { name: 'Documentation' })).getByText('README.md'),
    ).toBeVisible();
    for (const flag of ['Private: No', 'Fork: No', 'Archived: No', 'Monorepo: No']) {
      expect(screen.getByText(flag)).toBeInTheDocument();
    }
    expect(screen.getByText(/Files: 3/)).toBeInTheDocument();
    expect(screen.getByText(/Read with: gh_cli/)).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('marks the flags that are on and explains a monorepo', () => {
    show({
      ...makeRepo('o'),
      is_private: true,
      is_monorepo: true,
      monorepo_signals: ['turbo.json'],
    });

    expect(screen.getByText('Private: Yes')).toHaveClass('on');
    expect(screen.getByText('Fork: No')).not.toHaveClass('on');
    expect(screen.getByText('Monorepo: Yes')).toHaveAttribute('title', 'turbo.json');
  });

  it('draws the languages as a bar with a legend', () => {
    show({
      ...makeRepo('o'),
      languages: [
        { name: 'Python', bytes: 750, percent: 75 },
        { name: 'Shell', bytes: 250, percent: 25 },
      ],
    });

    expect(screen.getByRole('img', { name: 'Python 75%, Shell 25%' })).toBeInTheDocument();
    expect(screen.getByText('75%')).toBeInTheDocument();
    expect(screen.getByText('Shell')).toBeInTheDocument();
  });

  it('says so when no language was found', () => {
    show({ ...makeRepo('o'), languages: [] });

    expect(screen.getByText('No languages were found.')).toBeInTheDocument();
  });

  it('folds the lists into closed sections with a count and opens them on click', async () => {
    show();

    const titles = ['Top level', 'Notable folders', 'Frameworks', 'Tooling', 'Project files'];
    for (const title of titles) {
      const summary = screen.getByText(title, { selector: '.accordion-title' }).closest('summary');
      expect(summary?.parentElement).not.toHaveAttribute('open');
      await userEvent.click(/** @type {HTMLElement} */ (summary));
      expect(summary?.parentElement).toHaveAttribute('open');
    }
    expect(screen.getByRole('row', { name: /Typer cli/ })).toBeInTheDocument();
    expect(
      screen.getByRole('row', { name: /pyproject.toml python repo 1.0.0/ }),
    ).toBeInTheDocument();
  });

  it('says so when a list is empty', () => {
    show({
      ...makeRepo('o'),
      frameworks: [],
      tooling: [],
      manifests: [],
      notable_dirs: [],
    });

    expect(screen.getByText('No frameworks were recognised.')).toBeInTheDocument();
    expect(screen.getByText(/No build, test, lint, CI/)).toBeInTheDocument();
    expect(screen.getByText('No project files were found.')).toBeInTheDocument();
    expect(screen.getByText('No notable folders were found.')).toBeInTheDocument();
  });

  it('lists what was not read only when something was skipped', () => {
    const { unmount } = show();
    expect(screen.getByText('Not read')).toBeInTheDocument();
    expect(screen.getByText('.env (secret)')).toBeInTheDocument();
    unmount();

    show({ ...makeRepo('o'), skipped: [] });
    expect(screen.queryByText('Not read')).not.toBeInTheDocument();
  });

  it('shows the warnings', () => {
    show({ ...makeRepo('o'), warnings: ['The languages could not be read.'] });

    expect(screen.getByText('The languages could not be read.')).toBeInTheDocument();
  });

  it('asks the parent to refresh', async () => {
    const { onRefresh } = show();

    await userEvent.click(screen.getByLabelText('Refresh'));

    expect(onRefresh).toHaveBeenCalledOnce();
  });

  it('disables the buttons while busy', () => {
    show(makeRepo('o'), { busy: true });

    expect(screen.getByLabelText('Refresh')).toHaveAttribute('disabled');
    expect(screen.getByLabelText('Refresh with AI')).toHaveAttribute('disabled');
  });

  it('shows what the AI would be sent, sends nothing until Proceed, then reloads', async () => {
    const calls = mockApi((_method, path) => {
      if (path.endsWith('/analysis/plan')) return PLAN;
      if (path.endsWith('/analysis')) return DONE;
      return undefined;
    });
    const { container, onReload } = show();

    await userEvent.click(screen.getByLabelText('Refresh with AI'));
    expect(await screen.findByText(/About 1300 tokens sent/)).toBeInTheDocument();
    expect(screen.getByText(/Package names: htmx/)).toBeInTheDocument();
    expect(calls.some((call) => call.path.endsWith('/analysis'))).toBe(false);
    expect(screen.getByLabelText('Refresh with AI')).toHaveAttribute('disabled');
    expect(await axe(container)).toHaveNoViolations();

    await userEvent.click(screen.getByLabelText('Proceed'));
    expect(
      await screen.findByText(/Saved 1 parser\(s\), 1 framework\(s\) and 1 tool\(s\)/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Skipped one\./)).toBeInTheDocument();
    expect(calls.filter((call) => call.path.endsWith('/analysis')).length).toBe(1);
    expect(onReload).toHaveBeenCalledOnce();
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
        return new Promise((resolve) => {
          finish = resolve;
        });
      }),
    );
    show();

    await userEvent.click(screen.getByLabelText('Refresh with AI'));
    await userEvent.click(await screen.findByLabelText('Proceed'));
    expect(await screen.findByText('The AI is reading the repository…')).toBeInTheDocument();

    finish(/** @type {any} */ ({ ok: true, status: 200, json: async () => DONE }));
    await screen.findByText(/Saved 1 parser/);
    expect(screen.queryByText('The AI is reading the repository…')).not.toBeInTheDocument();
  });

  it('does not reload when the AI saved nothing', async () => {
    mockApi((_method, path) => {
      if (path.endsWith('/analysis/plan')) return PLAN;
      if (path.endsWith('/analysis')) return { ...DONE, parsers: [], frameworks: [], tools: [] };
      return undefined;
    });
    const { onReload } = show();

    await userEvent.click(screen.getByLabelText('Refresh with AI'));
    await userEvent.click(await screen.findByLabelText('Proceed'));

    expect(await screen.findByText(/Saved 0 parser\(s\)/)).toBeInTheDocument();
    expect(onReload).not.toHaveBeenCalled();
  });

  it('cancels the AI question without sending anything', async () => {
    const calls = mockApi((_method, path) => (path.endsWith('/analysis/plan') ? PLAN : undefined));
    show();

    await userEvent.click(screen.getByLabelText('Refresh with AI'));
    await userEvent.click(await screen.findByLabelText('Cancel'));

    expect(screen.queryByLabelText('Proceed')).not.toBeInTheDocument();
    expect(calls.some((call) => call.path.endsWith('/analysis'))).toBe(false);
  });

  it('says so when there is nothing to ask the AI', async () => {
    mockApi((_method, path) => (path.endsWith('/analysis/plan') ? NO_WORK : undefined));
    show();

    await userEvent.click(screen.getByLabelText('Refresh with AI'));

    expect(await screen.findByText(/nothing to ask the AI/)).toBeInTheDocument();
    expect(screen.queryByLabelText('Proceed')).not.toBeInTheDocument();
  });
});

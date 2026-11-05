import { afterEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import StudioPage from './Studio.jsx';
import { createBackend, mockApi, typeInto } from '../testing.js';

afterEach(() => vi.unstubAllGlobals());

const READ = '/api/v1/studio/repositories';

describe('StudioPage', () => {
  it('reads the repository, shows what was found and refreshes it', async () => {
    const backend = createBackend([]);
    const calls = mockApi(backend.handler);
    const { container } = render(<StudioPage visible onOpenSettings={() => undefined} />);

    expect(await screen.findByText(/the GitHub CLI/)).toBeInTheDocument();
    expect(screen.getByText('Next')).toHaveAttribute('disabled');
    typeInto(await screen.findByLabelText('Repository address'), 'https://github.com/o/repo');
    await userEvent.click(screen.getByText('Next'));

    expect(await screen.findByRole('heading', { name: 'o/repo' })).toBeInTheDocument();
    expect(screen.getByText('MIT')).toBeInTheDocument();
    expect(screen.getByRole('row', { name: /tests\/ tests/ })).toBeInTheDocument();
    expect(
      screen.getByRole('row', { name: /pyproject.toml python repo 1.0.0/ }),
    ).toBeInTheDocument();
    expect(screen.getByText('2 (+1 dev)')).toBeInTheDocument();
    expect(screen.getByRole('cell', { name: 'name = "repo"' })).toBeInTheDocument();
    expect(screen.getByText('Monorepo').parentElement).toHaveTextContent('No');
    expect(screen.getByText('Documentation').parentElement).toHaveTextContent(
      'README.md, CHANGELOG.md, LICENSE, docs/',
    );
    expect(screen.getByText('Not read').parentElement).toHaveTextContent('.env (secret)');
    expect(screen.getByRole('row', { name: /Python 750 75%/ })).toBeInTheDocument();
    expect(calls.find((call) => call.path === READ).body).toEqual({
      source: 'https://github.com/o/repo',
    });
    expect(await axe(container)).toHaveNoViolations();

    await userEvent.click(screen.getByText('Refresh'));
    await screen.findByRole('heading', { name: 'o/repo' });
    expect(calls.filter((call) => call.path === READ).at(-1).body.refresh).toBe(true);
  });

  it('asks a local folder for the details git cannot give', async () => {
    const backend = createBackend([]);
    backend.state.github = { mode: 'local_folder', local_folder: 'C:\\code' };
    const calls = mockApi(backend.handler);
    render(<StudioPage visible onOpenSettings={() => undefined} />);

    typeInto(await screen.findByLabelText('Repository folder'), 'C:\\code\\proj');
    await userEvent.click(screen.getByText('Next'));

    expect(await screen.findByRole('heading', { name: 'About this repository' })).toBeVisible();
    expect(await screen.findByLabelText('Repository name')).toHaveProperty('value', 'proj');
    expect(screen.getByText('Continue')).toHaveAttribute('disabled');
    typeInto(screen.getByLabelText('Owner'), 'me');
    typeInto(screen.getByLabelText('License'), 'MIT');
    typeInto(screen.getByLabelText('Topics (optional)'), 'cli, python');
    await userEvent.click(screen.getByText('Continue'));

    expect(await screen.findByRole('heading', { name: 'me/repo' })).toBeInTheDocument();
    const body = calls.find((call) => call.path === READ).body;
    expect(body.details).toMatchObject({
      owner: 'me',
      repo: 'proj',
      license: 'MIT',
      default_branch: 'main',
      topics: ['cli', 'python'],
    });
  });

  it('shows why a repository was rejected and links to Settings', async () => {
    mockApi(createBackend([]).handler);
    const open = vi.fn();
    render(<StudioPage visible onOpenSettings={open} />);

    typeInto(await screen.findByLabelText('Repository address'), 'nonsense');
    await userEvent.click(screen.getByText('Next'));
    expect(await screen.findByRole('alert')).toHaveTextContent('Use a GitHub address.');

    await userEvent.click(screen.getByRole('button', { name: 'Change in Settings' }));
    expect(open).toHaveBeenCalled();
  });
});

const NO_WORK = {
  provider: '',
  label: '',
  model: '',
  files: [],
  dependencies: [],
  names: [],
  tool_files: [],
  input_tokens: 0,
  max_output_tokens: 0,
};
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

async function openRepository() {
  typeInto(await screen.findByLabelText('Repository address'), 'https://github.com/o/repo');
  await userEvent.click(screen.getByText('Next'));
  await screen.findByRole('heading', { name: 'o/repo' });
}

describe('StudioPage AI step', () => {
  it('asks the AI once and sends nothing until the user proceeds', async () => {
    const backend = createBackend([]);
    const done = {
      parsers: ['ruby-gemfile'],
      frameworks: ['htmx'],
      tools: ['earthly'],
      skipped: [],
      input_tokens: 1230,
      output_tokens: 390,
    };
    const calls = mockApi((method, path, body) => {
      if (path.endsWith('/analysis/plan')) return PLAN;
      if (path.endsWith('/analysis')) return done;
      return backend.handler(method, path, body);
    });
    const { container } = render(<StudioPage visible onOpenSettings={() => undefined} />);
    await openRepository();
    expect(screen.getByText('Typer')).toBeInTheDocument();

    await userEvent.click(screen.getByText('Refresh with AI'));
    expect(await screen.findByText(/About 1300 tokens sent/)).toBeInTheDocument();
    expect(calls.some((call) => call.path.endsWith('/analysis'))).toBe(false);
    expect(await axe(container)).toHaveNoViolations();

    await userEvent.click(screen.getByText('Proceed'));
    expect(
      await screen.findByText(/Saved 1 parser\(s\), 1 framework\(s\) and 1 tool\(s\)/),
    ).toBeInTheDocument();
    expect(calls.filter((call) => call.path.endsWith('/analysis')).length).toBe(1);
    expect(calls.filter((call) => call.path === READ).at(-1).body.refresh).toBe(true);
  });

  it('says so when nothing needs the AI', async () => {
    const backend = createBackend([]);
    mockApi((method, path, body) => {
      if (path.endsWith('/analysis/plan')) return NO_WORK;
      return backend.handler(method, path, body);
    });
    render(<StudioPage visible onOpenSettings={() => undefined} />);
    await openRepository();

    await userEvent.click(screen.getByText('Refresh with AI'));
    expect(await screen.findByText(/nothing to ask the AI/)).toBeInTheDocument();
  });
});

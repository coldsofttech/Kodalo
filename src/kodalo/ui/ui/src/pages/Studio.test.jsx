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
    expect(screen.getByText('Monorepo').parentElement).toHaveTextContent('No');
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

describe('StudioPage AI step', () => {
  it('shows the token estimate and sends nothing until the user proceeds', async () => {
    const backend = createBackend([]);
    const plan = {
      provider: 'claude_api',
      label: 'Claude API',
      model: 'claude-haiku-5-5',
      files: ['Gemfile'],
      input_tokens: 900,
      max_output_tokens: 700,
    };
    const result = { added: ['ruby-gemfile'], skipped: [], input_tokens: 850, output_tokens: 300 };
    const calls = mockApi((method, path, body) => {
      if (path.endsWith('/parsers/plan')) return plan;
      if (path.endsWith('/parsers')) return result;
      return backend.handler(method, path, body);
    });
    const { container } = render(<StudioPage visible onOpenSettings={() => undefined} />);

    typeInto(await screen.findByLabelText('Repository address'), 'https://github.com/o/repo');
    await userEvent.click(screen.getByText('Next'));
    await screen.findByRole('heading', { name: 'o/repo' });

    await userEvent.click(screen.getByText('Refresh with AI'));
    expect(await screen.findByText(/About 900 tokens sent/)).toBeInTheDocument();
    expect(calls.some((call) => call.path.endsWith('/parsers'))).toBe(false);
    expect(await axe(container)).toHaveNoViolations();

    await userEvent.click(screen.getByText('Proceed'));
    expect(await screen.findByText(/Saved 1 parser/)).toBeInTheDocument();
    expect(calls.filter((call) => call.path === READ).at(-1).body.refresh).toBe(true);
    expect(screen.getByText('Refresh with AI')).toBeInTheDocument();
  });

  it('says so when no project file needs the AI', async () => {
    const backend = createBackend([]);
    mockApi((method, path, body) =>
      path.endsWith('/parsers/plan')
        ? { provider: '', label: '', model: '', files: [], input_tokens: 0, max_output_tokens: 0 }
        : backend.handler(method, path, body),
    );
    render(<StudioPage visible onOpenSettings={() => undefined} />);
    typeInto(await screen.findByLabelText('Repository address'), 'https://github.com/o/repo');
    await userEvent.click(screen.getByText('Next'));
    await screen.findByRole('heading', { name: 'o/repo' });

    await userEvent.click(screen.getByText('Refresh with AI'));
    expect(await screen.findByText(/nothing to ask the AI/)).toBeInTheDocument();
  });
});

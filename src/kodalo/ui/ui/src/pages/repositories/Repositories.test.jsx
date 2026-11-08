import { afterEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import RepositoriesPage from './Repositories.jsx';
import { createBackend, mockApi, typeInto, clickWhenReady } from '../../testing.js';

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

afterEach(() => vi.unstubAllGlobals());

const REPOSITORIES = '/api/v1/repositories';

function emptyBackend() {
  const backend = createBackend([]);
  backend.state.repos = [];
  return backend;
}

describe('RepositoriesPage', () => {
  it('lists the added repositories', async () => {
    mockApi(createBackend([]).handler);
    const { container } = render(<RepositoriesPage visible onOpenSettings={() => undefined} />);

    expect(await screen.findByRole('row', { name: /o\/repo main MIT/ })).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('adds a repository by its address', async () => {
    const calls = mockApi(emptyBackend().handler);
    render(<RepositoriesPage visible onOpenSettings={() => undefined} />);

    expect(await screen.findByText('No repositories yet.')).toBeInTheDocument();
    expect(screen.getByLabelText('Add')).toHaveAttribute('disabled');
    typeInto(await screen.findByLabelText('Repository address'), 'https://github.com/o/repo');
    await clickWhenReady(screen.getByLabelText('Add'));

    expect(await screen.findByRole('heading', { name: 'o/repo' })).toBeInTheDocument();
    expect(calls.find((call) => call.method === 'POST' && call.path === REPOSITORIES).body).toEqual(
      { source: 'https://github.com/o/repo' },
    );
  });

  it('removes a repository', async () => {
    const calls = mockApi(createBackend([]).handler);
    render(<RepositoriesPage visible onOpenSettings={() => undefined} />);

    await userEvent.click(await screen.findByLabelText('Remove o/repo'));

    expect(await screen.findByText('No repositories yet.')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Removed o/repo.');
    expect(calls.some((call) => call.method === 'DELETE')).toBe(true);
  });

  it('asks a local folder for the details git cannot give', async () => {
    const backend = emptyBackend();
    backend.state.github = { mode: 'local_folder', local_folder: 'C:\\code' };
    const calls = mockApi(backend.handler);
    render(<RepositoriesPage visible onOpenSettings={() => undefined} />);

    typeInto(await screen.findByLabelText('Repository folder'), 'C:\\code\\proj');
    await clickWhenReady(screen.getByLabelText('Add'));

    expect(await screen.findByRole('heading', { name: 'About this repository' })).toBeVisible();
    await waitFor(async () =>
      expect(await screen.findByLabelText('Repository name')).toHaveProperty('value', 'proj'),
    );
    expect(screen.getByLabelText('Add')).toHaveAttribute('disabled');
    typeInto(screen.getByLabelText('Owner'), 'me');
    typeInto(screen.getByLabelText('License'), 'MIT');
    typeInto(screen.getByLabelText('Topics (optional)'), 'cli, python');
    await clickWhenReady(screen.getByLabelText('Add'));

    expect(await screen.findByRole('heading', { name: 'me/repo' })).toBeInTheDocument();
    const body = calls.find((call) => call.method === 'POST' && call.path === REPOSITORIES).body;
    expect(body.details).toMatchObject({
      owner: 'me',
      repo: 'proj',
      license: 'MIT',
      default_branch: 'main',
      topics: ['cli', 'python'],
    });
  });

  it('shows why a repository was rejected and links to Settings', async () => {
    mockApi(emptyBackend().handler);
    const open = vi.fn();
    render(<RepositoriesPage visible onOpenSettings={open} />);

    typeInto(await screen.findByLabelText('Repository address'), 'nonsense');
    await clickWhenReady(screen.getByLabelText('Add'));
    expect(await screen.findByRole('alert')).toHaveTextContent('Use a GitHub address.');

    await userEvent.click(screen.getByRole('button', { name: 'Change in Settings' }));
    expect(open).toHaveBeenCalled();
  });

  it('shows what was read when Edit is pressed, refreshes it and goes back', async () => {
    const calls = mockApi(createBackend([]).handler);
    const { container } = render(<RepositoriesPage visible onOpenSettings={() => undefined} />);

    await userEvent.click(await screen.findByLabelText('Edit o/repo'));

    expect(await screen.findByRole('heading', { name: 'o/repo' })).toBeInTheDocument();
    expect(screen.getByText('MIT')).toBeInTheDocument();
    expect(screen.getByRole('row', { name: /tests\/ tests/ })).toBeInTheDocument();
    expect(
      screen.getByRole('row', { name: /pyproject.toml python repo 1.0.0/ }),
    ).toBeInTheDocument();
    expect(screen.getByText('2 (+1 dev)')).toBeInTheDocument();
    expect(screen.getByText(/Monorepo: No/)).toBeInTheDocument();
    expect(screen.getByText('Not read').parentElement).toHaveTextContent('.env (secret)');
    expect(screen.getByRole('img', { name: 'Python 75%' })).toBeInTheDocument();
    expect(screen.getByText('75%')).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();

    await userEvent.click(screen.getByLabelText('Refresh'));
    await screen.findByRole('heading', { name: 'o/repo' });
    const read = calls.filter((call) => call.method === 'POST' && call.path === REPOSITORIES);
    expect(read.at(-1).body).toEqual({ source: 'https://github.com/o/repo', refresh: true });

    await userEvent.click(screen.getByLabelText('Repositories home'));
    expect(await screen.findByRole('heading', { name: 'Your repositories' })).toBeVisible();
  });

  it('folds the file lists into sections that start closed', async () => {
    mockApi(createBackend([]).handler);
    render(<RepositoriesPage visible onOpenSettings={() => undefined} />);
    await userEvent.click(await screen.findByLabelText('Edit o/repo'));
    await screen.findByRole('heading', { name: 'o/repo' });

    for (const title of [
      'Top level',
      'Notable folders',
      'Frameworks',
      'Tooling',
      'Project files',
    ]) {
      const summary = screen.getByText(title, { selector: '.accordion-title' }).closest('summary');
      expect(summary?.parentElement).not.toHaveAttribute('open');
      await userEvent.click(summary);
      expect(summary?.parentElement).toHaveAttribute('open');
    }
  });

  it('shows the social preview only when the repository has one', async () => {
    const backend = createBackend([]);
    mockApi(backend.handler);
    const { unmount } = render(<RepositoriesPage visible onOpenSettings={() => undefined} />);
    await userEvent.click(await screen.findByLabelText('Edit o/repo'));
    await screen.findByRole('heading', { name: 'o/repo' });
    expect(screen.queryByRole('img', { name: /Social preview/ })).not.toBeInTheDocument();
    unmount();

    backend.state.repos = [{ ...backend.state.repos[0], has_social_preview: true }];
    render(<RepositoriesPage visible onOpenSettings={() => undefined} />);
    await userEvent.click(await screen.findByLabelText('Edit o/repo'));
    expect(screen.queryByRole('img', { name: /Social preview/ })).not.toBeInTheDocument();
    await userEvent.click(screen.getByLabelText('Social preview'));
    const image = await screen.findByRole('img', { name: 'Social preview of o/repo' });
    expect(image).toHaveAttribute(
      'src',
      expect.stringContaining('/repositories/r1/social-preview'),
    );
  });

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
    const { container } = render(<RepositoriesPage visible onOpenSettings={() => undefined} />);
    await userEvent.click(await screen.findByLabelText('Edit o/repo'));
    await screen.findByRole('heading', { name: 'o/repo' });
    expect(screen.getByText('Typer')).toBeInTheDocument();

    await userEvent.click(screen.getByLabelText('Refresh with AI'));
    expect(await screen.findByText(/About 1300 tokens sent/)).toBeInTheDocument();
    expect(calls.some((call) => call.path.endsWith('/analysis'))).toBe(false);
    expect(await axe(container)).toHaveNoViolations();

    await userEvent.click(screen.getByLabelText('Proceed'));
    expect(
      await screen.findByText(/Saved 1 parser\(s\), 1 framework\(s\) and 1 tool\(s\)/),
    ).toBeInTheDocument();
    expect(calls.filter((call) => call.path.endsWith('/analysis')).length).toBe(1);
    const read = calls.filter((call) => call.method === 'POST' && call.path === REPOSITORIES);
    expect(read.at(-1).body.refresh).toBe(true);
  });

  it('says so when nothing needs the AI', async () => {
    const backend = createBackend([]);
    mockApi((method, path, body) => {
      if (path.endsWith('/analysis/plan')) return NO_WORK;
      return backend.handler(method, path, body);
    });
    render(<RepositoriesPage visible onOpenSettings={() => undefined} />);
    await userEvent.click(await screen.findByLabelText('Edit o/repo'));
    await screen.findByRole('heading', { name: 'o/repo' });

    await userEvent.click(screen.getByLabelText('Refresh with AI'));
    expect(await screen.findByText(/nothing to ask the AI/)).toBeInTheDocument();
  });
});

async function openRepository() {
  await userEvent.click(await screen.findByLabelText('Edit o/repo'));
  await screen.findByRole('heading', { name: 'o/repo' });
  await userEvent.click(screen.getByLabelText('Next'));
  await screen.findByText('Purpose', { selector: '.accordion-title' });
}

const README = {
  repository_id: 'r1',
  tagline: 'Repo cleans things.',
  summary: 'Repo cleans things. It is fast.',
  purpose_file: 'README.md',
  installation: [
    {
      method: 'pip',
      command: 'pip install repo',
      note: '',
      evidence: { file: 'README.md', quote: 'pip install repo', status: 'documented' },
    },
  ],
  capabilities: [
    {
      name: 'Clean caches',
      description: 'remove caches',
      note: '',
      evidence: { file: 'README.md', quote: '- Clean caches', status: 'documented' },
    },
    {
      name: 'Service',
      description: '',
      note: 'Planned or experimental',
      evidence: { file: 'README.md', quote: '- Service', status: 'documented' },
    },
  ],
  features: [],
  use_cases: [],
  documents: [
    { path: 'README.md', status: 'read', reason: '', size: 100 },
    { path: 'SECURITY.md', status: 'skipped', reason: 'not about using the product', size: 0 },
  ],
  warnings: [],
  analyzed_at: 'now',
  use_cases_at: null,
};
const README_PLAN = {
  provider: 'claude_api',
  label: 'Claude API',
  model: 'claude-haiku-5-5',
  documents: ['README.md', 'docs/cli.md'],
  input_tokens: 400,
  max_output_tokens: 900,
};

describe('RepositoriesPage Analyze step', () => {
  it('reads the README on Next, asks once before sending, and shows the use cases', async () => {
    const backend = createBackend([]);
    let saved = README;
    const calls = mockApi((method, path, body) => {
      if (path.endsWith('/readme/analysis/plan')) return README_PLAN;
      if (path.endsWith('/readme/analysis')) {
        saved = {
          ...README,
          use_cases: [
            {
              title: 'Free disk space',
              description: 'Clean caches.',
              evidence: { file: 'README.md', quote: '- Clean caches', status: 'inferred' },
            },
          ],
        };
        return {
          installation: 1,
          capabilities: 2,
          features: 0,
          use_cases: 1,
          skipped: [],
          input_tokens: 400,
          output_tokens: 90,
        };
      }
      if (path.endsWith('/readme') && method === 'GET') return saved;
      if (path.endsWith('/readme')) return saved;
      return backend.handler(method, path, body);
    });
    const { container } = render(<RepositoriesPage visible onOpenSettings={() => undefined} />);
    await openRepository();

    expect(
      await screen.findByText('Purpose', { selector: '.accordion-title' }),
    ).toBeInTheDocument();
    expect(screen.getByText('pip install repo')).toBeInTheDocument();
    expect(
      screen.getByRole('row', { name: /Clean caches remove caches README.md/ }),
    ).toBeInTheDocument();
    expect(screen.getByText('Planned or experimental')).toBeInTheDocument();
    expect(screen.queryByText('SECURITY.md')).not.toBeInTheDocument(); // documents are not listed
    const read = calls.filter((call) => call.path.endsWith('/readme')).at(-1);
    expect(read.body).toEqual({ refresh: false });

    await userEvent.click(screen.getByLabelText('Refresh with AI'));
    expect(await screen.findByText(/About 400 tokens sent/)).toBeInTheDocument();
    expect(calls.some((call) => call.path.endsWith('/readme/analysis'))).toBe(false);
    expect(await axe(container)).toHaveNoViolations();

    await userEvent.click(screen.getByLabelText('Proceed'));
    expect(
      await screen.findByText(
        /Saved 1 installation method\(s\), 2 capabilities, 0 feature\(s\) and 1 use case/,
      ),
    ).toBeInTheDocument();
    expect(await screen.findByText('Free disk space')).toBeInTheDocument();
    expect(calls.filter((call) => call.path.endsWith('/readme/analysis')).length).toBe(1);
  });

  it('refreshes the documents and goes back to the repository', async () => {
    const backend = createBackend([]);
    const calls = mockApi((method, path, body) =>
      path.endsWith('/readme') ? README : backend.handler(method, path, body),
    );
    render(<RepositoriesPage visible onOpenSettings={() => undefined} />);
    await openRepository();

    expect(screen.getByRole('heading', { name: 'o/repo' })).toBeInTheDocument(); // same top bar
    expect(screen.getByLabelText('Next')).toHaveAttribute('disabled');
    expect(screen.getByLabelText('Back')).not.toHaveAttribute('disabled');
    await userEvent.click(screen.getByLabelText('Refresh'));
    await screen.findByText('Purpose', { selector: '.accordion-title' });
    expect(calls.filter((call) => call.path.endsWith('/readme')).at(-1).body.refresh).toBe(true);

    await userEvent.click(screen.getByLabelText('Back'));
    expect(await screen.findByRole('heading', { name: 'Languages' })).toBeVisible();
    expect(screen.getByLabelText('Back')).toHaveAttribute('disabled');
  });

  it('says so when there is nothing to send', async () => {
    const backend = createBackend([]);
    mockApi((method, path, body) => {
      if (path.endsWith('/readme/analysis/plan')) return { ...README_PLAN, documents: [] };
      if (path.endsWith('/readme')) return { ...README, capabilities: [], installation: [] };
      return backend.handler(method, path, body);
    });
    render(<RepositoriesPage visible onOpenSettings={() => undefined} />);
    await openRepository();

    expect(await screen.findByText(/No features or commands were listed/)).toBeInTheDocument();
    await userEvent.click(screen.getByLabelText('Refresh with AI'));
    expect(await screen.findByText(/so there is nothing to send/)).toBeInTheDocument();
  });
});

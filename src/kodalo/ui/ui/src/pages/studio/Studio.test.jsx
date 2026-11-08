import { afterEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import StudioPage from './Studio.jsx';
import { createBackend, mockApi } from '../../testing.js';

afterEach(() => vi.unstubAllGlobals());

describe('StudioPage', () => {
  it('picks a saved repository and goes to the Focus step', async () => {
    const backend = createBackend([]);
    const calls = mockApi((method, path, body) =>
      path.endsWith('/readme') ? README : backend.handler(method, path, body),
    );
    const { container } = render(<StudioPage visible onOpenRepositories={() => undefined} />);

    expect(await screen.findByRole('heading', { name: 'Choose a repository' })).toBeVisible();
    expect(await screen.findByRole('option', { name: 'o/repo' })).toBeInTheDocument();
    await userEvent.click(screen.getByLabelText('Next'));

    expect(await screen.findByRole('radiogroup', { name: 'Post type' })).toBeVisible();
    expect(calls.some((call) => call.path === '/api/v1/repositories/r1')).toBe(true);
    expect(screen.queryByText('Analyze', { selector: 'li' })).not.toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('asks to set the repository up first when its analysis is incomplete', async () => {
    const backend = createBackend([]);
    mockApi((method, path, body) =>
      path.endsWith('/readme')
        ? { ...README, features: [], use_cases_at: null }
        : backend.handler(method, path, body),
    );
    const open = vi.fn();
    render(<StudioPage visible onOpenRepositories={open} />);

    expect(await screen.findByRole('option', { name: 'o/repo' })).toBeInTheDocument();
    await userEvent.click(screen.getByLabelText('Next'));

    expect(await screen.findByRole('alert')).toHaveTextContent(/features.*use cases/);
    expect(screen.getByRole('heading', { name: 'Choose a repository' })).toBeVisible();
    await userEvent.click(screen.getByRole('button', { name: 'Open Repositories' }));
    expect(open).toHaveBeenCalled();
  });

  it('says so when no repository was added and links to Repositories', async () => {
    const backend = createBackend([]);
    backend.state.repos = [];
    mockApi(backend.handler);
    const open = vi.fn();
    render(<StudioPage visible onOpenRepositories={open} />);

    expect(await screen.findByText(/No repositories yet/)).toBeInTheDocument();
    expect(screen.getByLabelText('Next')).toHaveAttribute('disabled');
    expect(screen.getByLabelText('Back')).toHaveAttribute('disabled');
    await userEvent.click(screen.getByRole('button', { name: 'Add or remove repositories' }));
    expect(open).toHaveBeenCalled();
  });
});

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
  features: [{ name: 'Clean caches', description: 'remove caches', evidence: [] }],
  use_cases: [],
  documents: [
    { path: 'README.md', status: 'read', reason: '', size: 100 },
    { path: 'SECURITY.md', status: 'skipped', reason: 'not about using the product', size: 0 },
  ],
  warnings: [],
  analyzed_at: 'now',
  use_cases_at: 'now',
};

import { afterEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AiTaskModels from './TaskModels.jsx';
import { mockApi } from '../../../testing.js';

afterEach(() => vi.unstubAllGlobals());

const TASKS = [
  { task: 'palette', label: 'Palette suggestion', description: '', model: null },
  { task: 'studio_copy', label: 'Studio copywriter', description: '', model: 'smart' },
];

const connection = (/** @type {string[]} */ models) => ({
  provider: 'claude_api',
  is_default: true,
  enabled: true,
  default_model: 'fast',
  models: models.map((name) => ({ name })),
});

/** @param {string[]} models */
const backend = (models) => (/** @type {string} */ method, /** @type {string} */ path) => {
  if (path.endsWith('/connections')) return [connection(models)];
  if (method === 'GET' && path.endsWith('/task-models')) return TASKS;
  if (method === 'PUT')
    return TASKS.map((t) => (t.task === 'palette' ? { ...t, model: 'fast' } : t));
  return undefined;
};

describe('AiTaskModels', () => {
  it('shows the saved choice per job and saves a change', async () => {
    const calls = mockApi(backend(['fast', 'smart']));
    const { container } = render(<AiTaskModels />);

    await waitFor(async () =>
      expect(await screen.findByLabelText('Studio copywriter')).toHaveValue('smart'),
    );
    await waitFor(() => expect(screen.getByLabelText('Palette suggestion')).toHaveValue(''));
    expect(screen.getByLabelText('Save models')).toBeDisabled();

    await userEvent.selectOptions(screen.getByLabelText('Palette suggestion'), 'fast');
    await userEvent.click(screen.getByLabelText('Save models'));

    expect(await screen.findByText('Saved.')).toBeInTheDocument();
    const put = calls.filter((call) => call.method === 'PUT');
    expect(put).toHaveLength(1);
    expect(put[0].path).toBe('/api/v1/settings/ai/task-models/palette');
    expect(put[0].body).toEqual({ model: 'fast' });
    expect(await axe(container)).toHaveNoViolations();
  });

  it('asks for a connection with models first', async () => {
    mockApi(backend([]));
    render(<AiTaskModels />);
    expect(await screen.findByText(/Save an AI connection and add its models/)).toBeInTheDocument();
  });
});

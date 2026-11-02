import { afterEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SettingsPage from './Settings.jsx';
import { createBackend, mockApi } from '../testing.js';

afterEach(() => vi.unstubAllGlobals());

describe('SettingsPage', () => {
  it('defaults to the gh CLI, saves another mode and tests it', async () => {
    const backend = createBackend([]);
    const calls = mockApi(backend.handler);
    const { container } = render(<SettingsPage />);

    const select = await screen.findByLabelText('Connect with');
    expect(select).toHaveProperty('value', 'gh_cli');
    await userEvent.selectOptions(select, 'web_fetch');
    await userEvent.click(screen.getByText('Save'));
    expect(await screen.findByText('Saved.')).toBeInTheDocument();
    expect(calls.find((call) => call.method === 'PUT').body).toEqual({
      mode: 'web_fetch',
      local_folder: '',
    });

    await userEvent.click(screen.getByText('Test saved connection'));
    expect(await screen.findByText('Works.')).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });
});

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
    expect(await screen.findByLabelText('Project files to read')).toBeInTheDocument();
    expect(select).toHaveProperty('value', 'gh_cli');
    await userEvent.selectOptions(select, 'web_fetch');
    await userEvent.click(screen.getByText('Save'));
    expect(await screen.findByText('Saved.')).toBeInTheDocument();
    expect(calls.find((call) => call.method === 'PUT').body).toEqual({
      mode: 'web_fetch',
      local_folder: '',
      manifest_limit: 10,
    });

    await userEvent.click(screen.getByText('Test saved connection'));
    expect(await screen.findByText('Works.')).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('defaults the theme to system, saves dark and applies it', async () => {
    const backend = createBackend([]);
    const calls = mockApi(backend.handler);
    const { container } = render(<SettingsPage />);

    await userEvent.click(await screen.findByRole('tab', { name: 'Appearance' }));
    const select = await screen.findByLabelText('Theme');
    expect(select).toHaveProperty('value', 'system');
    await userEvent.selectOptions(select, 'dark');
    await userEvent.click(screen.getByText('Save'));
    expect(await screen.findByText('Saved.')).toBeInTheDocument();
    expect(calls.find((call) => call.method === 'PUT').body).toEqual({ theme: 'dark' });
    expect(document.documentElement.dataset.theme).toBe('dark');
    expect(await axe(container)).toHaveNoViolations();
  });
});

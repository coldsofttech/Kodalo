import { afterEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SettingsPage from './Settings.jsx';
import { createBackend, mockApi } from '../../testing.js';

afterEach(() => vi.unstubAllGlobals());

describe('SettingsPage', () => {
  it('opens on GitHub and switches between the tabs', async () => {
    mockApi(createBackend([]).handler);
    const { container } = render(<SettingsPage />);

    expect(screen.getAllByRole('tab').map((tab) => tab.textContent)).toEqual([
      'GitHub',
      'AI',
      'Platforms',
      'Appearance',
    ]);
    expect(screen.getByRole('tab', { name: 'GitHub' })).toHaveAttribute('aria-selected', 'true');
    expect(await screen.findByLabelText('Connect with')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('tab', { name: 'Appearance' }));
    expect(await screen.findByLabelText('Theme')).toBeInTheDocument();
    expect(screen.queryByLabelText('Connect with')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('tab', { name: 'AI' }));
    expect(await screen.findByLabelText('Provider')).toBeInTheDocument();
    expect(screen.queryByLabelText('Theme')).not.toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('loads the AI history only once it is expanded', async () => {
    const calls = mockApi(createBackend([]).handler);
    render(<SettingsPage />);

    await userEvent.click(screen.getByRole('tab', { name: 'AI' }));
    await screen.findByLabelText('Provider');
    const asked = () => calls.some((call) => call.path.includes('/settings/ai/history?'));
    expect(asked()).toBe(false);

    await userEvent.click(screen.getByText('View AI history'));
    expect(
      await screen.findByRole('table', { name: 'AI calls, newest first' }),
    ).toBeInTheDocument();
    expect(asked()).toBe(true);
  });
});

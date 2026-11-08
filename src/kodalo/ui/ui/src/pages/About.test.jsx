import { afterEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import About from './About.jsx';
import { DOCTOR, mockApi } from '../testing.js';

afterEach(() => vi.unstubAllGlobals());

const APP_INFO = { available: true, result: { name: 'Kodalo', version: '0.1.0' } };

describe('About', () => {
  it('shows the version and checks the installation on request', async () => {
    const calls = mockApi((method, path) => {
      if (path === '/api/bridge/app_info') return APP_INFO;
      if (path === '/api/v1/doctor') return DOCTOR;
    });
    const { container } = render(<About />);

    expect(await screen.findByText('Version 0.1.0')).toBeInTheDocument();
    expect(calls.some((call) => call.path === '/api/v1/doctor')).toBe(false);

    await userEvent.click(screen.getByText('Check installation'));

    expect(await screen.findByText('Everything looks good.')).toBeInTheDocument();
    expect(screen.getByRole('table', { name: 'Installation checks' })).toBeInTheDocument();
    expect(screen.getByRole('rowheader', { name: 'Python' }).parentElement).toHaveTextContent(
      'OK3.11.9 (requires 3.11+)',
    );
    expect(screen.getByRole('rowheader', { name: 'Fonts' }).parentElement).toHaveTextContent(
      'Warning',
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it('says when a required check failed', async () => {
    const failed = {
      healthy: false,
      checks: [{ name: 'Python', ok: false, detail: '3.9', required: true }],
    };
    mockApi((method, path) => {
      if (path === '/api/bridge/app_info') return APP_INFO;
      if (path === '/api/v1/doctor') return failed;
    });
    render(<About />);

    await userEvent.click(screen.getByText('Check installation'));

    expect(await screen.findByText('One or more required checks failed.')).toBeInTheDocument();
    expect(screen.getByRole('rowheader', { name: 'Python' }).parentElement).toHaveTextContent(
      'Failed',
    );
  });

  it('works without the version and shows why a check could not be run', async () => {
    mockApi((method, path) => {
      if (path === '/api/bridge/app_info') return { available: false, reason: 'No window' };
      if (path === '/api/v1/doctor') return [500, { detail: 'The check could not be run.' }];
    });
    render(<About />);

    await userEvent.click(screen.getByText('Check installation'));

    expect(await screen.findByRole('alert')).toHaveTextContent('The check could not be run.');
    expect(screen.queryByText(/^Version/)).not.toBeInTheDocument();
    expect(screen.getByText('Check installation')).not.toHaveAttribute('disabled');
  });
});

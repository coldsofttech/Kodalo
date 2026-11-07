import { afterEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Logs from './Logs.jsx';
import { createBackend, mockApi } from '../../testing.js';

afterEach(() => vi.unstubAllGlobals());

describe('Logs', () => {
  it('defaults to INFO and 90 days, and saves a new level', async () => {
    const calls = mockApi(createBackend([]).handler);
    const { container } = render(<Logs />);

    const select = await screen.findByLabelText('Log level');
    expect(select).toHaveProperty('value', 'INFO');
    expect(await screen.findByText(/C:\/Kodalo\/logs/)).toBeInTheDocument();

    await userEvent.selectOptions(select, 'DEBUG');
    await userEvent.click(screen.getByLabelText('Save'));
    expect(await screen.findByText('Saved.')).toBeInTheDocument();
    expect(calls.findLast((call) => call.method === 'PUT').body).toEqual({
      level: 'DEBUG',
      retention_days: 90,
    });
    expect(await axe(container)).toHaveNoViolations();
  });
});

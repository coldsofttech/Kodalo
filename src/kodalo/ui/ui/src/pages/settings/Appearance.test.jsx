import { afterEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Appearance from './Appearance.jsx';
import { createBackend, mockApi } from '../../testing.js';

afterEach(() => {
  vi.unstubAllGlobals();
  delete document.documentElement.dataset.theme;
});

describe('Appearance', () => {
  it('defaults the theme to system, saves dark and applies it', async () => {
    const calls = mockApi(createBackend([]).handler);
    const { container } = render(<Appearance />);

    const select = await screen.findByLabelText('Theme');
    expect(select).toHaveProperty('value', 'system');
    const choices = Array.from(select.querySelectorAll('option')).map((o) => o.textContent);
    expect(choices).toEqual(['System (default)', 'Light', 'Dark']);

    await userEvent.selectOptions(select, 'dark');
    await userEvent.click(screen.getByLabelText('Save'));
    expect(await screen.findByText('Saved.')).toBeInTheDocument();
    expect(calls.findLast((call) => call.method === 'PUT').body).toEqual({ theme: 'dark' });
    expect(document.documentElement.dataset.theme).toBe('dark');
    expect(await axe(container)).toHaveNoViolations();
  });

  it('shows the saved theme when the page opens', async () => {
    const backend = createBackend([]);
    mockApi(backend.handler);
    const first = render(<Appearance />);
    await userEvent.selectOptions(await screen.findByLabelText('Theme'), 'light');
    await userEvent.click(screen.getByLabelText('Save'));
    await screen.findByText('Saved.');
    first.unmount();

    render(<Appearance />);
    await vi.waitFor(() => expect(screen.getByLabelText('Theme')).toHaveProperty('value', 'light'));
  });
});

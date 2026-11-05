import { afterEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AiHistory from './AiHistory.jsx';
import { createBackend, mockApi, setChecked, typeInto } from '../../testing.js';

afterEach(() => vi.unstubAllGlobals());

describe('AiHistory', () => {
  it('shows the usage per connection and model, the chart and the calls', async () => {
    const calls = mockApi(createBackend([]).handler);
    const { container } = render(<AiHistory />);

    const usage = await screen.findByRole('table', {
      name: 'Token usage per connection and model',
    });
    expect(within(usage).getByText('Claude API')).toBeInTheDocument();
    expect(within(usage).getAllByText('1,200')).toHaveLength(2);
    expect(screen.getByRole('img', { name: /Tokens per day from 2026-11-03/ })).toBeInTheDocument();

    const history = screen.getByRole('table', { name: 'AI calls, newest first' });
    expect(within(history).getByText('Palette')).toBeInTheDocument();
    expect(within(history).getByText('Failed')).toBeInTheDocument();
    expect(calls.some((call) => call.path.includes('period=week'))).toBe(true);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('asks the API again when the period changes, including a custom range', async () => {
    const calls = mockApi(createBackend([]).handler);
    render(<AiHistory />);
    await screen.findByRole('table', { name: 'AI calls, newest first' });

    await userEvent.selectOptions(screen.getByLabelText('Show'), 'month');
    await vi.waitFor(() =>
      expect(calls.some((call) => call.path.includes('period=month'))).toBe(true),
    );

    await userEvent.selectOptions(screen.getByLabelText('Show'), 'custom');
    expect(screen.getByText('Choose a first day, a last day, or both.')).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('From'), '2026-11-01');
    await vi.waitFor(() =>
      expect(
        calls.some(
          (call) => call.path.includes('period=custom') && call.path.includes('start=2026-11-01'),
        ),
      ).toBe(true),
    );
  });

  it('opens the text of a call, and says so when it was not kept', async () => {
    mockApi(createBackend([]).handler);
    const { container } = render(<AiHistory />);

    await userEvent.click(await screen.findByLabelText(/Details of Suggest a palette/));
    const dialog = await screen.findByRole('dialog', { name: 'Suggest a palette' });
    expect(within(dialog).getByText('The prompt that was sent.')).toBeInTheDocument();
    expect(within(dialog).getByText('{"answer": true}')).toBeInTheDocument();
    expect(within(dialog).getByText(/1,200 sent, 300 received/)).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
    await userEvent.click(within(dialog).getByText('Close'));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

    await userEvent.click(screen.getByLabelText(/Details of Frameworks and tooling/));
    const failed = await screen.findByRole('dialog', { name: /Frameworks and tooling/ });
    expect(within(failed).getByText(/Failed: Claude Code did not answer/)).toBeInTheDocument();
    expect(within(failed).getByText(/The text was not kept/)).toBeInTheDocument();
    await userEvent.keyboard('{Escape}');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('saves the history settings', async () => {
    const calls = mockApi(createBackend([]).handler);
    render(<AiHistory />);
    await screen.findByRole('table', { name: 'AI calls, newest first' });

    setChecked(screen.getByLabelText('Keep the text of prompts and answers'), true);
    typeInto(screen.getByLabelText('Remove entries after (days)'), '30');
    await userEvent.click(screen.getByText('Save history settings'));
    expect(await screen.findByText('Saved.')).toBeInTheDocument();
    expect(calls.findLast((call) => call.method === 'PUT').body).toEqual({
      store_text: true,
      retention_days: 30,
    });
  });

  it('purges only after a confirmation', async () => {
    const calls = mockApi(createBackend([]).handler);
    render(<AiHistory />);
    await screen.findByRole('table', { name: 'AI calls, newest first' });

    await userEvent.click(screen.getByText('Purge history'));
    expect(calls.some((call) => call.method === 'DELETE')).toBe(false);
    await userEvent.click(screen.getByText('Cancel'));
    expect(screen.queryByText('Remove the whole AI history?')).not.toBeInTheDocument();

    await userEvent.click(screen.getByText('Purge history'));
    await userEvent.click(screen.getByText('Yes, purge everything'));
    expect(await screen.findByText('Removed 2 entries.')).toBeInTheDocument();
    expect(await screen.findByText('No calls in this period.')).toBeInTheDocument();
  });
});

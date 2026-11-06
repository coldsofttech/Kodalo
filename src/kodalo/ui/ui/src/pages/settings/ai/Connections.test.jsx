import { afterEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AiConnections from './Connections.jsx';
import { createBackend, mockApi, typeInto } from '../../../testing.js';

afterEach(() => vi.unstubAllGlobals());

const choose = async (/** @type {string} */ name) =>
  userEvent.selectOptions(await screen.findByLabelText('Provider'), name);

const put = (/** @type {any[]} */ calls, /** @type {string} */ suffix) =>
  calls.findLast((call) => call.method === 'PUT' && call.path.endsWith(suffix));

describe('AiConnections', () => {
  it('lists the four providers, saves a key without showing it, and tests it', async () => {
    const calls = mockApi(createBackend([]).handler);
    const { container } = render(<AiConnections />);

    const provider = await screen.findByLabelText('Provider');
    const names = Array.from(provider.querySelectorAll('option')).map((o) => o.textContent);
    expect(names).toEqual([
      'Choose a provider',
      'Claude API',
      'Claude Code',
      'ChatGPT API',
      'Gemini API',
    ]);
    expect(screen.queryByLabelText('Claude API key')).not.toBeInTheDocument();

    await choose('Claude API');
    expect(screen.getByLabelText('Claude API key')).toHaveAttribute('type', 'password');

    typeInto(screen.getByLabelText('Claude API key'), 'sk-test-1234567890abcdef');
    await userEvent.click(screen.getByLabelText('Save Claude API'));
    expect(await screen.findByText('Saved.')).toBeInTheDocument();
    expect(put(calls, '/claude_api').body).toEqual({
      enabled: true,
      api_key: 'sk-test-1234567890abcdef',
      base_url: '',
    });
    expect(await screen.findByText(/A key ending in cdef is saved/)).toBeInTheDocument();
    expect(screen.queryByDisplayValue('sk-test-1234567890abcdef')).not.toBeInTheDocument();

    await userEvent.click(screen.getByLabelText('Test Claude API'));
    expect(await screen.findByText('Connected. 2 models available.')).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('turning a connection on makes it the one used, and it can be removed', async () => {
    const calls = mockApi(createBackend([]).handler);
    render(<AiConnections />);

    await choose('Claude Code');
    expect(screen.queryByLabelText('Claude Code key')).not.toBeInTheDocument();
    await userEvent.click(screen.getByLabelText('Save Claude Code'));
    await screen.findByText('Saved.');
    expect(put(calls, '/claude_code').body).toEqual({ enabled: true });
    expect(put(calls, '/default').body).toEqual({ provider: 'claude_code' });

    await userEvent.click(screen.getByLabelText('Remove Claude Code'));
    expect(await screen.findByText('Removed.')).toBeInTheDocument();
  });

  it('refreshes models, adds one with settings and chooses a default', async () => {
    const calls = mockApi(createBackend([]).handler);
    const { container } = render(<AiConnections />);

    await choose('Claude Code');
    await userEvent.click(screen.getByLabelText('Save Claude Code'));
    await userEvent.click(await screen.findByLabelText('Refresh Claude Code models'));
    expect(await screen.findByText('2 models available.')).toBeInTheDocument();
    expect(await screen.findByRole('rowheader', { name: 'm-a' })).toBeInTheDocument();

    const nameBox = screen.getByLabelText('Claude Code model name');
    const suggestions = nameBox.list?.querySelectorAll('option') ?? [];
    expect(Array.from(suggestions).map((option) => option.value)).toEqual(['m-a', 'm-b']);
    await userEvent.type(nameBox, 'mine');
    typeInto(screen.getByLabelText('Claude Code max tokens'), '500');
    typeInto(screen.getByLabelText('Claude Code temperature'), '0.5');
    await userEvent.click(screen.getByLabelText('Save Claude Code model'));
    expect(await screen.findByText('Model saved.')).toBeInTheDocument();
    expect(put(calls, '/models/mine').body).toEqual({
      max_tokens: 500,
      temperature: 0.5,
      timeout_s: null,
    });

    await userEvent.click(screen.getByLabelText('Remove m-a'));
    await vi.waitFor(() => expect(screen.queryByRole('rowheader', { name: 'm-a' })).toBeNull());
    expect(await axe(container)).toHaveNoViolations();
  });

  it('shows a number problem instead of sending it', async () => {
    const calls = mockApi(createBackend([]).handler);
    render(<AiConnections />);

    await choose('Claude Code');
    await userEvent.click(screen.getByLabelText('Save Claude Code'));
    await userEvent.type(await screen.findByLabelText('Claude Code model name'), 'mine');
    typeInto(screen.getByLabelText('Claude Code max tokens'), 'lots');
    await userEvent.click(screen.getByLabelText('Save Claude Code model'));
    expect(await screen.findByRole('alert')).toHaveTextContent('max tokens must be a number.');
    expect(put(calls, '/models/mine')).toBeUndefined();
  });

  it('loads the saved settings when a saved model is chosen', async () => {
    mockApi(createBackend([]).handler);
    render(<AiConnections />);

    await choose('Claude Code');
    await userEvent.click(screen.getByLabelText('Save Claude Code'));
    await userEvent.type(await screen.findByLabelText('Claude Code model name'), 'mine');
    typeInto(screen.getByLabelText('Claude Code max tokens'), '500');
    await userEvent.click(screen.getByLabelText('Save Claude Code model'));
    await screen.findByText('Model saved.');
    expect(screen.getByLabelText('Claude Code max tokens')).toHaveProperty('value', '');

    await userEvent.type(screen.getByLabelText('Claude Code model name'), 'mine');
    expect(screen.getByLabelText('Claude Code max tokens')).toHaveProperty('value', '500');
  });
});

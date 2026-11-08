import { afterEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen, waitFor } from '@testing-library/react';
import AiIdeaCount from './IdeaCount.jsx';
import { mockApi, typeInto, clickWhenReady } from '../../../testing.js';

afterEach(() => vi.unstubAllGlobals());

describe('AiIdeaCount', () => {
  it('shows the saved number and saves a new one', async () => {
    const calls = mockApi((method, _path, body) => (method === 'PUT' ? body : { idea_count: 5 }));
    const { container } = render(<AiIdeaCount />);

    const field = await screen.findByLabelText('Post ideas per request');
    await waitFor(() => expect(field).toHaveValue('5'));
    expect(screen.getByLabelText('Save post ideas')).toBeDisabled();

    typeInto(field, '12');
    await clickWhenReady(screen.getByLabelText('Save post ideas'));

    expect(await screen.findByText('Saved.')).toBeInTheDocument();
    expect(calls.findLast((call) => call.method === 'PUT').body).toEqual({ idea_count: 12 });
    expect(await axe(container)).toHaveNoViolations();
  });

  it('does not allow a number outside 1 to 20', async () => {
    mockApi(() => ({ idea_count: 5 }));
    render(<AiIdeaCount />);

    typeInto(await screen.findByLabelText('Post ideas per request'), '21');

    expect(screen.getByLabelText('Save post ideas')).toBeDisabled();
  });
});

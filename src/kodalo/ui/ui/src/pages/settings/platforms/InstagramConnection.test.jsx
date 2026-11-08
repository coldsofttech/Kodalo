import { afterEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import InstagramConnection from './InstagramConnection.jsx';
import { createBackend, mockApi, typeInto, clickWhenReady } from '../../../testing.js';

afterEach(() => vi.unstubAllGlobals());

describe('InstagramConnection', () => {
  it('connects with a pasted token, shows only its last characters and disconnects', async () => {
    const calls = mockApi(createBackend([]).handler);
    const { container } = render(<InstagramConnection />);

    expect(await screen.findByText(/Not connected/)).toBeInTheDocument();
    expect(screen.getByText('How to get an access token')).toBeInTheDocument();
    expect(screen.getByText('Cloudflared')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: "Open Instagram's guide" })).toHaveProperty(
      'href',
      expect.stringContaining('developers.facebook.com'),
    );
    expect(screen.getByLabelText('Connect')).toBeDisabled();
    typeInto(screen.getByLabelText('Access token'), 'IGAAsecret1234');
    expect(screen.getByLabelText('Connect')).toBeDisabled();
    typeInto(screen.getByLabelText('Instagram account ID'), '1784140');
    await clickWhenReady(screen.getByLabelText('Connect'));

    expect(await screen.findByText('Connected.')).toBeInTheDocument();
    expect(screen.getByText('sweepito')).toBeInTheDocument();
    expect(screen.getByText(/ending in 1234/)).toBeInTheDocument();
    expect(screen.getByLabelText('Access token')).toHaveProperty('value', '');
    expect(screen.getByLabelText('Instagram account ID')).toHaveProperty('value', '');
    expect(calls.find((call) => call.method === 'PUT').body).toEqual({
      access_token: 'IGAAsecret1234',
      account_id: '1784140',
    });
    expect(await axe(container)).toHaveNoViolations();

    await userEvent.click(screen.getByLabelText('Disconnect'));
    expect(await screen.findByText('Disconnected.')).toBeInTheDocument();
    expect(screen.getByText(/Not connected/)).toBeInTheDocument();
  });

  it('shows why a token was refused', async () => {
    mockApi(createBackend([]).handler);
    render(<InstagramConnection />);

    typeInto(await screen.findByLabelText('Access token'), 'bad');
    typeInto(screen.getByLabelText('Instagram account ID'), '1784140');
    await clickWhenReady(screen.getByLabelText('Connect'));

    expect(await screen.findByRole('alert')).toHaveTextContent('Instagram rejected the token.');
  });
});

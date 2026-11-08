import { afterEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import GitHub from './GitHub.jsx';
import { createBackend, mockApi, typeInto, clickWhenReady } from '../../testing.js';

afterEach(() => vi.unstubAllGlobals());

const put = (/** @type {any[]} */ calls) => calls.findLast((call) => call.method === 'PUT');

describe('GitHub', () => {
  it('defaults to the gh CLI, saves another mode and tests it', async () => {
    const calls = mockApi(createBackend([]).handler);
    const { container } = render(<GitHub />);

    const select = await screen.findByLabelText('Connect with');
    await waitFor(() => expect(select).toHaveProperty('value', 'gh_cli'));
    await userEvent.selectOptions(select, 'web_fetch');
    await userEvent.click(screen.getByLabelText('Save connection'));
    expect(await screen.findByText('Saved.')).toBeInTheDocument();
    expect(put(calls).body).toEqual({
      mode: 'web_fetch',
      local_folder: '',
      manifest_limit: 10,
      document_limit: 10,
      document_max_kb: 200,
    });

    await userEvent.click(screen.getByLabelText('Test saved connection'));
    expect(await screen.findByText('Works.')).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('asks for a folder only for the local folder mode', async () => {
    const calls = mockApi(createBackend([]).handler);
    render(<GitHub />);

    const select = await screen.findByLabelText('Connect with');
    expect(screen.queryByLabelText('Folder')).not.toBeInTheDocument();
    await userEvent.selectOptions(select, 'local_folder');
    typeInto(screen.getByLabelText('Folder'), 'C:/repos');
    await clickWhenReady(screen.getByLabelText('Save connection'));
    expect(await screen.findByText('Saved.')).toBeInTheDocument();
    expect(put(calls).body).toMatchObject({ mode: 'local_folder', local_folder: 'C:/repos' });
  });

  it('shows the reading limits and saves them on their own', async () => {
    const calls = mockApi(createBackend([]).handler);
    render(<GitHub />);

    await waitFor(async () =>
      expect(await screen.findByLabelText('Project files to read')).toHaveProperty('value', '10'),
    );
    await waitFor(() =>
      expect(screen.getByLabelText('Documents to read')).toHaveProperty('value', '10'),
    );
    expect(screen.getByLabelText('Most of each document to read (KB)')).toHaveProperty(
      'value',
      '200',
    );
    typeInto(screen.getByLabelText('Documents to read'), '5');
    await clickWhenReady(screen.getByLabelText('Save reading limits'));
    expect(await screen.findByText('Saved.')).toBeInTheDocument();
    expect(put(calls).body).toMatchObject({ document_limit: 5 });
  });
});

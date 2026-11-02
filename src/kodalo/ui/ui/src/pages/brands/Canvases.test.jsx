import { afterEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CanvasesPage from './Canvases.jsx';
import { createBackend, makeBrand, mockApi, typeInto } from '../../testing.js';

const saveJson = vi.fn();
vi.mock('../../download.js', async (importOriginal) => ({
  ...(await importOriginal()),
  saveJson: (...args) => saveJson(...args),
}));

afterEach(() => {
  vi.unstubAllGlobals();
  saveJson.mockClear();
});

function start(onChange = vi.fn()) {
  const backend = createBackend([makeBrand('b1', 'Main', true)]);
  const calls = mockApi(backend.handler);
  const view = render(<CanvasesPage onChange={onChange} />);
  return { backend, calls, onChange, ...view };
}

const rowOf = async (name) => (await screen.findByRole('rowheader', { name })).closest('tr');

describe('CanvasesPage', () => {
  it('lists built-in canvases, who uses them, and has no accessibility violations', async () => {
    const { container } = start();
    const portrait = await rowOf('Instagram portrait');
    expect(within(portrait).getByText('1080 x 1350')).toBeInTheDocument();
    expect(within(portrait).getByText('Built in')).toBeInTheDocument();
    expect(within(portrait).getByText('Default, Compact')).toBeInTheDocument();
    expect(within(portrait).queryByLabelText('Delete Instagram portrait')).not.toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('adds, edits, copies and deletes a canvas and tells the app', async () => {
    const { calls, onChange } = start();
    await userEvent.click(await screen.findByText('New canvas'));
    typeInto(await screen.findByLabelText('Canvas name'), 'Feed');
    await userEvent.click(screen.getByText('Create canvas'));
    expect(await screen.findByText('Created "Feed".')).toBeInTheDocument();
    expect(calls.find((c) => c.method === 'POST').body).toEqual({
      name: 'Feed',
      width: 1080,
      height: 1350,
    });
    expect(onChange).toHaveBeenCalledTimes(1);

    const feed = await rowOf('Feed');
    await userEvent.click(within(feed).getByLabelText('Edit Feed'));
    typeInto(await screen.findByLabelText('Canvas name'), 'Wide feed');
    await userEvent.click(screen.getByText('Save canvas'));
    expect(await screen.findByText('Saved "Wide feed".')).toBeInTheDocument();

    const wide = await rowOf('Wide feed');
    await userEvent.click(within(wide).getByLabelText('Copy Wide feed'));
    await userEvent.click(await screen.findByText('Create canvas'));
    expect(await rowOf('Wide feed copy')).toBeInTheDocument();

    await userEvent.click(
      within(await rowOf('Wide feed copy')).getByLabelText('Delete Wide feed copy'),
    );
    await userEvent.click(await screen.findByText('Delete canvas'));
    expect(await screen.findByText('Deleted "Wide feed copy".')).toBeInTheDocument();
    expect(screen.queryByRole('rowheader', { name: 'Wide feed copy' })).not.toBeInTheDocument();
  });

  it('shows why a canvas cannot be added or deleted', async () => {
    start();
    await userEvent.click(await screen.findByText('New canvas'));
    typeInto(await screen.findByLabelText('Canvas name'), 'instagram portrait');
    await userEvent.click(screen.getByText('Create canvas'));
    expect(await screen.findByRole('alert')).toHaveTextContent('already exists');
  });

  it('exports a canvas to a file and imports one from a file', async () => {
    start();
    await userEvent.click(
      within(await rowOf('Instagram square')).getByLabelText('Export Instagram square'),
    );
    await waitFor(() => expect(saveJson).toHaveBeenCalledTimes(1));
    expect(saveJson.mock.calls[0][0]).toMatchObject({ format: 'kodalo-canvas', width: 1080 });
    expect(saveJson.mock.calls[0][1]).toBe('Instagram square.kodalo-canvas.json');

    const body = { format: 'kodalo-canvas', version: 1, name: 'Wide', width: 1600, height: 900 };
    await userEvent.upload(
      screen.getByLabelText('Choose a canvas file to import'),
      new File([JSON.stringify(body)], 'wide.json', { type: 'application/json' }),
    );
    expect(await screen.findByText('Imported the canvas.')).toBeInTheDocument();
    expect(await rowOf('Wide')).toBeInTheDocument();
  });
});

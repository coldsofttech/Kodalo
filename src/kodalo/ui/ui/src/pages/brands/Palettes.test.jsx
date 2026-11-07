import { afterEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PalettesPage from './Palettes.jsx';
import { SAMPLE_DATA, createBackend, makeBrand, mockApi, typeInto } from '../../testing.js';

const saveJson = vi.fn();
vi.mock('../../libs/download.js', async (importOriginal) => ({
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
  const view = render(<PalettesPage onChange={onChange} />);
  return { backend, calls, onChange, ...view };
}

const rowOf = async (name) => (await screen.findByRole('rowheader', { name })).closest('tr');

describe('PalettesPage', () => {
  it('lists built-in palettes and has no accessibility violations', async () => {
    const { container } = start();
    const midnight = await rowOf('Midnight');
    expect(within(midnight).getByText('Built in')).toBeInTheDocument();
    expect(within(midnight).queryByLabelText('Delete Midnight')).not.toBeInTheDocument();
    expect(within(midnight).queryByLabelText('Edit Midnight')).not.toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('adds, edits, copies, exports and deletes a palette and tells the app', async () => {
    const { calls, onChange } = start();
    await userEvent.click(await screen.findByLabelText('New palette'));
    typeInto(await screen.findByLabelText('Palette name'), 'Ocean');
    await userEvent.click(screen.getByLabelText('Create palette'));
    expect(await screen.findByText('Created "Ocean".')).toBeInTheDocument();
    const post = calls.find((call) => call.method === 'POST');
    expect(post.body.name).toBe('Ocean');
    expect(post.body.colors.primary.light).toBe('#2563eb');
    expect(onChange).toHaveBeenCalledTimes(1);

    await userEvent.click(within(await rowOf('Ocean')).getByLabelText('Edit Ocean'));
    typeInto(await screen.findByLabelText('Palette name'), 'Sea');
    await userEvent.click(screen.getByLabelText('Save palette'));
    expect(await screen.findByText('Saved "Sea".')).toBeInTheDocument();

    await userEvent.click(within(await rowOf('Sea')).getByLabelText('Copy Sea'));
    await userEvent.click(await screen.findByLabelText('Create palette'));
    expect(await rowOf('Sea copy')).toBeInTheDocument();

    await userEvent.click(within(await rowOf('Sea')).getByLabelText('Export Sea'));
    await waitFor(() => expect(saveJson).toHaveBeenCalledTimes(1));
    expect(saveJson.mock.calls[0][0].format).toBe('kodalo-palette');
    expect(saveJson.mock.calls[0][1]).toBe('Sea.kodalo-palette.json');

    await userEvent.click(within(await rowOf('Sea copy')).getByLabelText('Delete Sea copy'));
    await userEvent.click(await screen.findByText('Delete palette'));
    expect(await screen.findByText('Deleted "Sea copy".')).toBeInTheDocument();
  });

  it('imports a palette from a file and shows why one cannot be added', async () => {
    start();
    const body = {
      format: 'kodalo-palette',
      version: 1,
      name: 'Paper',
      colors: SAMPLE_DATA().colors,
    };
    await userEvent.upload(
      await screen.findByLabelText('Choose a palette file to import'),
      new File([JSON.stringify(body)], 'paper.json', { type: 'application/json' }),
    );
    expect(await screen.findByText('Imported the palette.')).toBeInTheDocument();
    expect(await rowOf('Paper (2)')).toBeInTheDocument();

    await userEvent.upload(
      screen.getByLabelText('Choose a palette file to import'),
      new File(['not json'], 'bad.json', { type: 'application/json' }),
    );
    expect(await screen.findByRole('alert')).toHaveTextContent('not valid JSON');

    await userEvent.click(screen.getByLabelText('New palette'));
    typeInto(await screen.findByLabelText('Palette name'), 'midnight');
    await userEvent.click(screen.getByLabelText('Create palette'));
    expect(await screen.findByRole('alert')).toHaveTextContent('already exists');
  });
});

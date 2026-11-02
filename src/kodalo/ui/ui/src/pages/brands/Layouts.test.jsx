import { afterEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LayoutsPage from './Layouts.jsx';
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
  const view = render(<LayoutsPage onChange={onChange} />);
  return { backend, calls, onChange, ...view };
}

const rowOf = async (name) => (await screen.findByRole('rowheader', { name })).closest('tr');

describe('LayoutsPage', () => {
  it('lists built-in layouts with their slide count and has no accessibility violations', async () => {
    const { container } = start();
    const standard = await rowOf('Default');
    expect(within(standard).getByText('Instagram portrait (1080 x 1350)')).toBeInTheDocument();
    expect(within(standard).getByText('6')).toBeInTheDocument();
    expect(within(standard).getByText('Main')).toBeInTheDocument();
    expect(within(standard).queryByLabelText('Delete Default')).not.toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('adds, edits, copies, exports and deletes a layout and tells the app', async () => {
    const { calls, onChange } = start();
    await userEvent.click(await screen.findByText('New layout'));
    typeInto(await screen.findByLabelText('Layout name'), 'Feed');
    typeInto(screen.getByLabelText('Number of slides'), '9');
    await userEvent.click(screen.getByText('Create layout'));
    expect(await screen.findByText('Created "Feed".')).toBeInTheDocument();
    const post = calls.find((call) => call.method === 'POST');
    expect(post.body.name).toBe('Feed');
    expect(post.body.settings.slides_count).toBe(9);
    expect(post.body.settings.canvas_id).toBe('system-instagram_portrait');
    expect(onChange).toHaveBeenCalledTimes(1);

    await userEvent.click(within(await rowOf('Feed')).getByLabelText('Edit Feed'));
    await userEvent.selectOptions(
      await screen.findByLabelText('Canvas'),
      'system-instagram_square',
    );
    typeInto(screen.getByLabelText('Footer text'), '@kodalo');
    await userEvent.click(screen.getByText('Save layout'));
    expect(await screen.findByText('Saved "Feed".')).toBeInTheDocument();
    const patch = calls.find((call) => call.method === 'PATCH');
    expect(patch.body.canvas_id).toBe('system-instagram_square');
    expect(patch.body.footer_text).toBe('@kodalo');

    await userEvent.click(within(await rowOf('Feed')).getByLabelText('Copy Feed'));
    await userEvent.click(await screen.findByText('Create layout'));
    expect(await rowOf('Feed copy')).toBeInTheDocument();

    await userEvent.click(within(await rowOf('Feed')).getByLabelText('Export Feed'));
    await waitFor(() => expect(saveJson).toHaveBeenCalledTimes(1));
    expect(saveJson.mock.calls[0][0].format).toBe('kodalo-layout');
    expect(saveJson.mock.calls[0][1]).toBe('Feed.kodalo-layout.json');

    await userEvent.click(within(await rowOf('Feed copy')).getByLabelText('Delete Feed copy'));
    await userEvent.click(await screen.findByText('Delete layout'));
    expect(await screen.findByText('Deleted "Feed copy".')).toBeInTheDocument();
  });

  it('imports a layout from a file and shows why one cannot be added', async () => {
    start();
    const body = { format: 'kodalo-layout', version: 1, name: 'Default', slides_count: 6 };
    await userEvent.upload(
      await screen.findByLabelText('Choose a layout file to import'),
      new File([JSON.stringify(body)], 'default.json', { type: 'application/json' }),
    );
    expect(await screen.findByText('Imported the layout.')).toBeInTheDocument();
    expect(await rowOf('Default (2)')).toBeInTheDocument();

    await userEvent.click(screen.getByText('New layout'));
    typeInto(await screen.findByLabelText('Layout name'), 'compact');
    await userEvent.click(screen.getByText('Create layout'));
    expect(await screen.findByRole('alert')).toHaveTextContent('already exists');
  });

  it('does not let a layout in use be deleted', async () => {
    const backend = createBackend([makeBrand('b1', 'Main', true)]);
    backend.state.layouts.push({
      ...backend.state.layouts[0],
      id: 'user-9',
      name: 'Mine',
      type: 'user',
    });
    backend.state.brands[0].data.layout_id = 'user-9';
    mockApi(backend.handler);
    render(<LayoutsPage />);
    await userEvent.click(within(await rowOf('Mine')).getByLabelText('Delete Mine'));
    await userEvent.click(await screen.findByText('Delete layout'));
    expect(await screen.findByRole('alert')).toHaveTextContent('is used by: Main');
  });
});

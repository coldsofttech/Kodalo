import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import BrandsPage from './Brands.jsx';
import { createBackend, makeBrand, mockApi, typeInto, clickWhenReady } from '../../testing.js';

const saveJson = vi.fn();
vi.mock('../../libs/download.js', async (importOriginal) => ({
  ...(await importOriginal()),
  saveJson: (...args) => saveJson(...args),
}));

/** @type {ReturnType<typeof createBackend>} */
let backend;
/** @type {ReturnType<typeof mockApi>} */
let calls;

function start(brands = [makeBrand('b1', 'Main', true), makeBrand('b2', 'Side')]) {
  backend = createBackend(brands);
  calls = mockApi(backend.handler);
  return render(<BrandsPage />);
}

const field = (label) => screen.findByLabelText(label);
const sent = (method, fragment) =>
  calls.filter((call) => call.method === method && call.path.includes(fragment));

describe('BrandsPage: first run', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('welcomes a new user and creates a brand from a palette', async () => {
    start([]);
    expect(await screen.findByRole('heading', { name: 'Welcome to Kodalo' })).toBeInTheDocument();

    await userEvent.click(screen.getByRole('radio', { name: /Paper/ }));
    typeInto(await field('Brand name'), 'Acme');
    await clickWhenReady(screen.getByText('Create brand'));

    expect(await screen.findByRole('heading', { name: 'Preview' })).toBeInTheDocument();
    expect(sent('POST', '/api/v1/brands')[0].body).toEqual({
      name: 'Acme',
      palette: 'system-paper',
    });
    await waitFor(async () => expect(await field('Brand name')).toHaveProperty('value', 'Acme'));
  });

  it('shows why creating failed', async () => {
    start([]);
    backend.state.brands = [makeBrand('x', 'Taken', true)];
    typeInto(await field('Brand name'), 'taken');
    await clickWhenReady(screen.getByText('Create brand'));

    expect(await screen.findByRole('alert')).toHaveTextContent('already exists');
  });

  it('has no accessibility violations', async () => {
    const { container } = start([]);
    await screen.findByRole('heading', { name: 'Welcome to Kodalo' });
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe('BrandsPage: editing', () => {
  beforeEach(() => {
    saveJson.mockReset();
  });
  afterEach(() => vi.unstubAllGlobals());

  it('lists brands, marks the default and opens it', async () => {
    start();
    const list = await screen.findByRole('complementary', { name: 'Brand profiles' });
    expect(within(list).getByRole('img', { name: 'Default brand' })).toBeInTheDocument();
    await waitFor(async () => expect(await field('Brand name')).toHaveProperty('value', 'Main'));
    expect(screen.getByRole('tab', { name: 'Colors', selected: true })).toBeInTheDocument();
  });

  it('shows the sample slides in the preview and follows the light/dark switch', async () => {
    start();
    await screen.findByRole('heading', { name: 'Preview' });
    for (const kind of ['cover', 'content', 'code', 'quote', 'cta']) {
      expect(screen.getByLabelText(`Sample ${kind} slide`)).toBeInTheDocument();
    }
    const strip = document.querySelector('.preview-strip');
    expect(strip.style.getPropertyValue('--b-background')).toBe('#ffffff');
    await userEvent.click(screen.getByRole('button', { name: 'Dark' }));
    await waitFor(() => expect(strip.style.getPropertyValue('--b-background')).toBe('#0b1020'));
  });

  it('updates the preview at once and saves only when asked', async () => {
    start();
    typeInto(await field('Background, light (hex)'), '#FF0000');

    const strip = document.querySelector('.preview-strip');
    await waitFor(() => expect(strip.style.getPropertyValue('--b-background')).toBe('#ff0000'));
    expect(screen.getByText('You have unsaved changes.')).toBeInTheDocument();
    expect(sent('PATCH', '/brands/')).toHaveLength(0);

    await userEvent.click(screen.getByLabelText('Save'));
    expect(await screen.findByText('Saved.')).toBeInTheDocument();
    const patch = sent('PATCH', '/brands/b1')[0];
    expect(patch.body.data.colors.background.light).toBe('#ff0000');
    expect(patch.body.name).toBe('Main');
    expect(screen.queryByText('You have unsaved changes.')).not.toBeInTheDocument();
  });

  it('does not accept a half-typed color', async () => {
    start();
    typeInto(await field('Text, dark (hex)'), '#12');

    expect(await screen.findByText('Use six hex digits, such as #2563eb.')).toBeInTheDocument();
    expect(screen.queryByText('You have unsaved changes.')).not.toBeInTheDocument();
  });

  it('accepts a color from the picker', async () => {
    start();
    const picker = await screen.findByLabelText('Primary, light color picker');
    fireEvent.change(picker, { target: { value: '#00ff00' } });

    await waitFor(async () =>
      expect(await field('Primary, light (hex)')).toHaveProperty('value', '#00ff00'),
    );
    expect(screen.getByText('You have unsaved changes.')).toBeInTheDocument();
  });

  it('discards edits', async () => {
    start();
    typeInto(await field('Brand name'), 'Renamed');
    await clickWhenReady(screen.getByLabelText('Discard'));

    await waitFor(async () => expect(await field('Brand name')).toHaveProperty('value', 'Main'));
    expect(screen.queryByText('You have unsaved changes.')).not.toBeInTheDocument();
  });

  it('renames through the same Save', async () => {
    start();
    typeInto(await field('Brand name'), 'Renamed');
    await clickWhenReady(screen.getByLabelText('Save'));

    await screen.findByText('Saved.');
    expect(sent('PATCH', '/brands/b1')[0].body.name).toBe('Renamed');
    expect(
      within(screen.getByRole('complementary', { name: 'Brand profiles' })).getByText('Renamed'),
    ).toBeInTheDocument();
  });

  it('shows the server message when saving fails', async () => {
    start();
    typeInto(await field('Brand name'), 'Side');
    await clickWhenReady(screen.getByLabelText('Save'));

    expect(await screen.findByRole('alert')).toHaveTextContent('already exists');
    expect(screen.getByText('You have unsaved changes.')).toBeInTheDocument();
  });

  it('asks before leaving unsaved changes', async () => {
    start();
    typeInto(await field('Brand name'), 'Edited');
    const list = screen.getByRole('complementary', { name: 'Brand profiles' });
    await userEvent.click(within(list).getByRole('button', { name: /Side/ }));

    expect(screen.getByRole('alertdialog', { name: 'Unsaved changes' })).toBeInTheDocument();
    await userEvent.click(screen.getByText('Keep editing'));
    await waitFor(async () => expect(await field('Brand name')).toHaveProperty('value', 'Edited'));

    await userEvent.click(within(list).getByRole('button', { name: /Side/ }));
    await userEvent.click(screen.getByText('Discard changes'));
    await waitFor(async () => expect(await field('Brand name')).toHaveProperty('value', 'Side'));
  });

  it('switches brands without asking when nothing changed', async () => {
    start();
    const list = await screen.findByRole('complementary', { name: 'Brand profiles' });
    await userEvent.click(within(list).getByRole('button', { name: /Side/ }));

    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    await waitFor(async () => expect(await field('Brand name')).toHaveProperty('value', 'Side'));
  });

  it('shows contrast problems without changing any color', async () => {
    start();
    backend.state.contrast = [
      { color: 'text', on: 'background', mode: 'light', ratio: 1.2, minimum: 4.5, passes: false },
    ];
    typeInto(await field('Text, light (hex)'), '#eeeeee');

    expect(await screen.findByText(/text on background, light: 1.2:1/)).toBeInTheDocument();
    expect(screen.getByText(/never changed for you/)).toBeInTheDocument();
    await waitFor(async () =>
      expect(await field('Text, light (hex)')).toHaveProperty('value', '#eeeeee'),
    );
  });

  it('reports good contrast', async () => {
    start();
    expect(await screen.findByText(/enough contrast/)).toBeInTheDocument();
  });

  it('changes fonts from the lists', async () => {
    start();
    await userEvent.click(await screen.findByRole('tab', { name: 'Fonts' }));
    await userEvent.selectOptions(screen.getByLabelText('Heading'), 'Lora');
    await userEvent.selectOptions(screen.getByLabelText('Monospace'), 'Segoe UI');

    const strip = document.querySelector('.preview-strip');
    expect(strip.style.getPropertyValue('--f-heading')).toBe('"Lora", sans-serif');
    await userEvent.click(screen.getByLabelText('Save'));
    const { fonts } = (await waitFor(() => sent('PATCH', '/brands/b1')[0])).body.data;
    expect(fonts.heading).toEqual({ family: 'Lora', source: 'bundled' });
    expect(fonts.mono).toEqual({ family: 'Segoe UI', source: 'system' });
  });

  it('marks a font that is not installed', async () => {
    backend = createBackend([
      (() => {
        const brand = makeBrand('b1', 'Main', true);
        brand.data.fonts.body = { family: 'Gone Font', source: 'system' };
        return brand;
      })(),
    ]);
    calls = mockApi(backend.handler);
    render(<BrandsPage />);
    await userEvent.click(await screen.findByRole('tab', { name: 'Fonts' }));

    expect(screen.getByRole('option', { name: 'Gone Font (not installed)' })).toBeInTheDocument();
  });

  it('chooses a shared layout and previews it', async () => {
    start();
    await userEvent.click(await screen.findByRole('tab', { name: 'Layout' }));
    const select = screen.getByRole('combobox', { name: 'Layout' });
    await waitFor(() => expect(select).toHaveProperty('value', 'system-default'));
    expect(screen.getByText('Instagram portrait (1080 x 1350)')).toBeInTheDocument();
    expect(screen.getByText('6')).toBeInTheDocument();

    await userEvent.selectOptions(select, 'system-compact');
    const strip = document.querySelector('.preview-strip');
    expect(strip.style.getPropertyValue('--align')).toBe('center');
    expect(screen.getByText('1/4')).toBeInTheDocument();
    expect(screen.getByText('You have unsaved changes.')).toBeInTheDocument();
    await userEvent.click(screen.getByLabelText('Save'));
    await waitFor(() =>
      expect(sent('PATCH', '/brands/b1')[0].body.data.layout_id).toBe('system-compact'),
    );
  });

  it('saves the colors of a brand as a palette', async () => {
    start();
    typeInto(await field('Palette name'), 'Ocean');
    await clickWhenReady(screen.getByLabelText('Save palette'));
    expect(await screen.findByText('Saved the palette "Ocean".')).toBeInTheDocument();
    expect(sent('POST', '/api/v1/brands/palettes')[0].body.name).toBe('Ocean');
    expect(backend.state.palettes.map((p) => p.name)).toContain('Ocean');
  });

  it('uploads and removes a logo straight away', async () => {
    start();
    await userEvent.click(await screen.findByRole('tab', { name: 'Logo' }));
    const file = new File(['png'], 'logo.png', { type: 'image/png' });
    await userEvent.upload(screen.getByLabelText('Choose logo file'), file);

    expect(await screen.findByAltText('Logo of Main')).toBeInTheDocument();
    const put = sent('PUT', '/brands/b1/logo')[0];
    expect(put.path).toContain('variant=light');
    expect(put.body).toBe(file);
    expect(screen.queryByText('You have unsaved changes.')).not.toBeInTheDocument();
    expect(document.querySelector('.slide-logo')).not.toBeNull();

    await userEvent.click(screen.getByText('Remove'));
    await waitFor(() => expect(screen.queryByAltText('Logo of Main')).not.toBeInTheDocument());
    expect(document.querySelector('.slide-logo')).toBeNull();
  });

  it('keeps unsaved edits when a logo is uploaded', async () => {
    start();
    typeInto(await field('Brand name'), 'Edited');
    await clickWhenReady(screen.getByRole('tab', { name: 'Logo' }));
    await userEvent.upload(
      screen.getByLabelText('Choose logo file'),
      new File(['png'], 'logo.png', { type: 'image/png' }),
    );

    await screen.findByAltText('Logo of Main');
    expect(screen.getByText('You have unsaved changes.')).toBeInTheDocument();
    typeInto(screen.getByLabelText('Padding (pixels)'), '100');
    await userEvent.selectOptions(screen.getByLabelText('Position'), 'bottom_right');
    await userEvent.selectOptions(screen.getByLabelText('Show on'), 'last');
    await waitFor(() => expect(document.querySelector('.slide-logo')).not.toBeNull());
    expect(document.querySelectorAll('.slide-logo')).toHaveLength(1);
  });

  it('shows why a logo was refused', async () => {
    start();
    const original = backend.handler;
    mockApi((method, path, body) =>
      method === 'PUT'
        ? [422, { detail: 'The SVG logo uses <script>, which is not allowed.' }]
        : original(method, path, body),
    );
    await userEvent.click(await screen.findByRole('tab', { name: 'Logo' }));
    await userEvent.upload(
      screen.getByLabelText('Choose logo file'),
      new File(['x'], 'bad.svg', { type: 'image/svg+xml' }),
    );

    expect(await screen.findByRole('alert')).toHaveTextContent('not allowed');
  });

  it('makes another brand the default', async () => {
    start();
    const list = await screen.findByRole('complementary', { name: 'Brand profiles' });
    await userEvent.click(within(list).getByRole('button', { name: /Side/ }));
    await userEvent.click(await screen.findByText('Make default'));

    expect(await screen.findByText('Default brand changed.')).toBeInTheDocument();
    expect(sent('POST', '/brands/b2/default')).toHaveLength(1);
  });

  it('duplicates a brand under a new name', async () => {
    start();
    await userEvent.click(await screen.findByLabelText('Duplicate'));
    await waitFor(async () =>
      expect(await field('Name of the copy')).toHaveProperty('value', 'Main copy'),
    );
    typeInto(await field('Name of the copy'), 'Third');
    await clickWhenReady(
      within(screen.getByRole('group', { name: 'Duplicate brand' })).getByText('Duplicate'),
    );

    expect(await screen.findByText('Created Third.')).toBeInTheDocument();
    expect(sent('POST', '/duplicate')[0].body).toEqual({ name: 'Third' });
    await waitFor(async () => expect(await field('Brand name')).toHaveProperty('value', 'Third'));
  });

  it('deletes only after confirmation', async () => {
    start();
    await userEvent.click(await screen.findByLabelText('Delete'));
    await userEvent.click(screen.getByText('Keep it'));
    expect(sent('DELETE', '/brands/b1')).toHaveLength(0);

    await userEvent.click(screen.getByLabelText('Delete'));
    await userEvent.click(screen.getByText('Delete brand'));
    expect(await screen.findByText('Deleted Main.')).toBeInTheDocument();
    await waitFor(async () => expect(await field('Brand name')).toHaveProperty('value', 'Side'));
  });

  it('exports a brand to a file', async () => {
    start();
    await userEvent.click(await screen.findByLabelText('Export'));

    await screen.findByText(/Exported/);
    expect(saveJson).toHaveBeenCalledOnce();
    expect(saveJson.mock.calls[0][0].format).toBe('kodalo-brand');
    expect(saveJson.mock.calls[0][1]).toBe('Main.kodalo-brand.json');
  });

  it('imports a brand file and rejects one that is not JSON', async () => {
    start();
    const input = await screen.findByLabelText('Choose a brand file to import');
    const good = new File(
      [JSON.stringify({ format: 'kodalo-brand', version: 1, name: 'Imported' })],
      'x.json',
      { type: 'application/json' },
    );
    await userEvent.upload(input, good);
    expect(await screen.findByText('Imported Imported.')).toBeInTheDocument();

    await userEvent.upload(input, new File(['nope'], 'bad.json', { type: 'application/json' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('not a Kodalo brand file');
  });

  it('creates another brand from the list', async () => {
    start();
    await userEvent.click(await screen.findByLabelText('New brand'));
    const group = screen.getByRole('group', { name: 'New brand' });
    typeInto(within(group).getByLabelText('Brand name'), 'Fresh');
    await clickWhenReady(within(group).getByText('Create brand'));

    expect(await screen.findByText('Created Fresh.')).toBeInTheDocument();
  });

  it('says so when the brands cannot be loaded', async () => {
    mockApi(() => [503, { detail: 'The local data cannot be opened.' }]);
    render(<BrandsPage />);

    expect(await screen.findByRole('alert')).toHaveTextContent('cannot be opened');
  });

  it('has no accessibility violations on any tab', async () => {
    const { container } = start();
    await screen.findByRole('heading', { name: 'Preview' });
    expect(await axe(container)).toHaveNoViolations();
    for (const name of ['Fonts', 'Logo', 'Layout']) {
      await userEvent.click(screen.getByRole('tab', { name }));
      expect(await axe(container)).toHaveNoViolations();
    }
  });

  it('moves between tabs with the arrow keys', async () => {
    start();
    const colors = await screen.findByRole('tab', { name: 'Colors' });
    colors.focus();
    await userEvent.keyboard('{ArrowRight}');
    expect(screen.getByRole('tab', { name: 'Fonts', selected: true })).toHaveFocus();
    await userEvent.keyboard('{ArrowLeft}{ArrowLeft}');
    expect(screen.getByRole('tab', { name: 'Layout', selected: true })).toHaveFocus();
  });
});

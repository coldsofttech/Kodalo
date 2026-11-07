import { afterEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ColorsPanel, FontsPanel, LayoutPanel, LogoPanel } from './editor.jsx';
import { COLOR_ROWS } from '../libs/brand.js';
import {
  CANVASES,
  FONTS,
  LAYOUTS,
  NO_FAILURES,
  SAMPLE_DATA,
  makeBrand,
  mockApi,
  typeInto,
} from '../testing.js';

afterEach(() => vi.unstubAllGlobals());

const [firstName, firstKey] = COLOR_ROWS[0];

describe('ColorsPanel', () => {
  it('has a light and a dark value for every color', () => {
    mockApi(() => NO_FAILURES);
    render(<ColorsPanel data={SAMPLE_DATA()} onChange={vi.fn()} />);
    expect(screen.getAllByRole('group').length).toBeGreaterThanOrEqual(COLOR_ROWS.length);
    for (const [name] of COLOR_ROWS) {
      expect(screen.getByLabelText(`${name}, light (hex)`)).toBeInTheDocument();
      expect(screen.getByLabelText(`${name}, dark color picker`)).toBeInTheDocument();
    }
  });

  it('reports a valid hex value in lower case and complains about an invalid one', () => {
    mockApi(() => NO_FAILURES);
    const onChange = vi.fn();
    render(<ColorsPanel data={SAMPLE_DATA()} onChange={onChange} />);
    const field = screen.getByLabelText(`${firstName}, light (hex)`);

    typeInto(field, '#ABCDEF');
    expect(onChange).toHaveBeenCalledWith(`colors.${firstKey}.light`, '#abcdef');

    onChange.mockClear();
    typeInto(field, '#12');
    expect(onChange).not.toHaveBeenCalled();
    expect(screen.getByText('Use six hex digits, such as #2563eb.')).toBeInTheDocument();
    expect(field).toHaveAttribute('aria-invalid', 'true');
  });

  it('reports a color picked with the color picker', () => {
    mockApi(() => NO_FAILURES);
    const onChange = vi.fn();
    render(<ColorsPanel data={SAMPLE_DATA()} onChange={onChange} />);
    fireEvent.change(screen.getByLabelText(`${firstName}, dark color picker`), {
      target: { value: '#123456' },
    });
    expect(onChange).toHaveBeenCalledWith(`colors.${firstKey}.dark`, '#123456');
  });

  it('says when every color has enough contrast', async () => {
    mockApi(() => NO_FAILURES);
    render(<ColorsPanel data={SAMPLE_DATA()} onChange={vi.fn()} />);
    expect(await screen.findByRole('status')).toHaveTextContent(
      'All colors have enough contrast in light and dark.',
    );
  });

  it('lists the pairs that need more contrast without changing the colors', async () => {
    const weak = {
      color: 'primary',
      on: 'background',
      mode: 'dark',
      ratio: 2.1,
      minimum: 4.5,
      passes: false,
    };
    mockApi(() => [...NO_FAILURES, weak]);
    render(<ColorsPanel data={SAMPLE_DATA()} onChange={vi.fn()} />);
    expect(await screen.findByRole('status')).toHaveTextContent('1 pair needs more contrast.');
    expect(
      screen.getByText('primary on background, dark: 2.1:1 (needs 4.5:1)'),
    ).toBeInTheDocument();
  });

  it('says so when the contrast cannot be checked', async () => {
    mockApi(() => undefined);
    render(<ColorsPanel data={SAMPLE_DATA()} onChange={vi.fn()} />);
    expect(await screen.findByText('Contrast could not be checked just now.')).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    mockApi(() => NO_FAILURES);
    const { container } = render(<ColorsPanel data={SAMPLE_DATA()} onChange={vi.fn()} />);
    await screen.findByRole('status');
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe('FontsPanel', () => {
  it('groups bundled and installed fonts and reports a change with its source', async () => {
    const onChange = vi.fn();
    render(<FontsPanel data={SAMPLE_DATA()} fonts={FONTS} onChange={onChange} />);
    const heading = screen.getByLabelText('Heading');
    expect(heading).toHaveValue('Poppins');
    await userEvent.selectOptions(heading, 'Segoe UI');
    expect(onChange).toHaveBeenCalledWith('fonts.heading', {
      family: 'Segoe UI',
      source: 'system',
    });
    await userEvent.selectOptions(heading, 'Lora');
    expect(onChange).toHaveBeenLastCalledWith('fonts.heading', {
      family: 'Lora',
      source: 'bundled',
    });
  });

  it('keeps a font that is no longer installed in the list', () => {
    const data = SAMPLE_DATA();
    data.fonts.body = { family: 'Gone Sans', source: 'system' };
    render(<FontsPanel data={data} fonts={FONTS} onChange={vi.fn()} />);
    expect(screen.getByLabelText('Body')).toHaveValue('Gone Sans');
    expect(screen.getByRole('option', { name: 'Gone Sans (not installed)' })).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <FontsPanel data={SAMPLE_DATA()} fonts={FONTS} onChange={vi.fn()} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe('LogoPanel', () => {
  const props = () => ({
    brand: makeBrand('b1', 'Acme'),
    data: SAMPLE_DATA(),
    onChange: vi.fn(),
    onStored: vi.fn(),
    onError: vi.fn(),
  });

  it('invites a first upload when there is no logo', () => {
    render(<LogoPanel {...props()} />);
    expect(screen.getByText('No logo yet.')).toBeInTheDocument();
    expect(screen.getByText('The main logo is used in dark mode.')).toBeInTheDocument();
    expect(screen.getAllByText('Choose file')).toHaveLength(2);
    expect(screen.queryByText('Remove')).not.toBeInTheDocument();
  });

  it('uploads the chosen file and hands the stored brand up', async () => {
    const stored = makeBrand('b1', 'Acme');
    const calls = mockApi(() => stored);
    const given = props();
    render(<LogoPanel {...given} />);
    const file = new File(['<svg/>'], 'logo.svg', { type: 'image/svg+xml' });
    await userEvent.upload(screen.getByLabelText('Choose logo file'), file);
    await vi.waitFor(() => expect(given.onStored).toHaveBeenCalledWith(stored));
    expect(calls).toEqual([
      expect.objectContaining({
        method: 'PUT',
        path: expect.stringContaining('/b1/logo?variant=light'),
      }),
    ]);
  });

  it('reports an upload that failed', async () => {
    mockApi(() => [422, { detail: 'Too big.' }]);
    const given = props();
    render(<LogoPanel {...given} />);
    const file = new File(['x'], 'logo.png', { type: 'image/png' });
    await userEvent.upload(screen.getByLabelText('Choose logo for dark mode file'), file);
    await vi.waitFor(() => expect(given.onError).toHaveBeenCalledTimes(1));
    expect(given.onStored).not.toHaveBeenCalled();
  });

  it('shows a stored logo and removes it', async () => {
    const stored = makeBrand('b1', 'Acme');
    const calls = mockApi(() => stored);
    const given = props();
    given.data.logo.file = 'logo.png';
    render(<LogoPanel {...given} />);
    expect(screen.getByRole('img', { name: 'Logo of Acme' })).toHaveAttribute(
      'src',
      expect.stringContaining('/b1/logo?variant=light'),
    );
    expect(screen.getByText('Replace')).toBeInTheDocument();
    await userEvent.click(screen.getByLabelText('Remove logo'));
    await vi.waitFor(() => expect(given.onStored).toHaveBeenCalledWith(stored));
    expect(calls[0]).toMatchObject({ method: 'DELETE' });
  });

  it('reports where and how big the logo is shown', async () => {
    const given = props();
    render(<LogoPanel {...given} />);
    await userEvent.selectOptions(screen.getByLabelText('Position'), 'bottom_right');
    expect(given.onChange).toHaveBeenCalledWith('logo.position', 'bottom_right');
    await userEvent.selectOptions(screen.getByLabelText('Show on'), 'first');
    expect(given.onChange).toHaveBeenCalledWith('logo.show_on', 'first');
    typeInto(screen.getByLabelText('Size (percent of width)'), '99');
    expect(given.onChange).toHaveBeenCalledWith('logo.size_percent', 60);
    typeInto(screen.getByLabelText('Padding (pixels)'), '12');
    expect(given.onChange).toHaveBeenCalledWith('logo.padding', 12);
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<LogoPanel {...props()} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe('LayoutPanel', () => {
  it('describes the chosen layout and its canvas', () => {
    render(
      <LayoutPanel data={SAMPLE_DATA()} layouts={LAYOUTS} canvases={CANVASES} onChange={vi.fn()} />,
    );
    expect(screen.getByLabelText('Layout')).toHaveValue('system-default');
    const details = screen.getByLabelText('Layout details');
    expect(details).toHaveTextContent('Instagram portrait (1080 x 1350)');
    expect(details).toHaveTextContent('top 96, sides 80, bottom 96');
    expect(details).toHaveTextContent('left, regular, slide numbers');
  });

  it('reports another layout', async () => {
    const onChange = vi.fn();
    render(
      <LayoutPanel
        data={SAMPLE_DATA()}
        layouts={LAYOUTS}
        canvases={CANVASES}
        onChange={onChange}
      />,
    );
    await userEvent.selectOptions(screen.getByLabelText('Layout'), 'system-compact');
    expect(onChange).toHaveBeenCalledWith('layout_id', 'system-compact');
  });

  it('hides the details of a layout that no longer exists', () => {
    const data = { ...SAMPLE_DATA(), layout_id: 'gone' };
    render(<LayoutPanel data={data} layouts={LAYOUTS} canvases={CANVASES} onChange={vi.fn()} />);
    expect(screen.queryByLabelText('Layout details')).not.toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <LayoutPanel data={SAMPLE_DATA()} layouts={LAYOUTS} canvases={CANVASES} onChange={vi.fn()} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});

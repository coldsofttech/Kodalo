import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Preview, { FullScreen } from './preview.jsx';
import { CANVASES, LAYOUTS, SAMPLE_DATA, makeBrand } from '../testing.js';

const brand = makeBrand('b1', 'Acme');

/** @param {Record<string, unknown>} [logo] */
const setup = (logo = {}) => {
  const data = SAMPLE_DATA();
  Object.assign(data.logo, logo);
  return render(<Preview brand={brand} data={data} layout={LAYOUTS[0]} canvas={CANVASES[0]} />);
};

describe('Preview', () => {
  it('draws the five sample slides with their footers', () => {
    setup();
    expect(
      screen
        .getAllByRole('figure')
        .map(
          (figure) => within(figure).getByText(/^[A-Z]/, { selector: 'figcaption' }).textContent,
        ),
    ).toEqual(['Cover', 'Content', 'Code', 'Quote', 'Call to action']);
    expect(screen.getByLabelText('Sample cover slide')).toHaveTextContent('1/6');
    expect(screen.getByLabelText('Sample cta slide')).toHaveTextContent('5/6');
  });

  it('switches between the light and dark colors', async () => {
    setup();
    expect(screen.getByRole('button', { name: 'Light' })).toHaveAttribute('aria-pressed', 'true');
    await userEvent.click(screen.getByRole('button', { name: 'Dark' }));
    expect(screen.getByRole('button', { name: 'Dark' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'Light' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('shows the logo only on the slides it is meant for', () => {
    const { container, unmount } = setup({ file: 'logo.png', show_on: 'all' });
    expect(container.querySelectorAll('.slide-logo')).toHaveLength(5);
    unmount();
    const first = setup({ file: 'logo.png', show_on: 'first' });
    expect(first.container.querySelectorAll('.slide-logo')).toHaveLength(1);
    first.unmount();
    const none = setup({ file: 'logo.png', show_on: 'none' });
    expect(none.container.querySelectorAll('.slide-logo')).toHaveLength(0);
    none.unmount();
    const missing = setup({ file: null, show_on: 'all' });
    expect(missing.container.querySelectorAll('.slide-logo')).toHaveLength(0);
  });

  it('uses the dark logo in dark mode when there is one', async () => {
    const { container } = setup({ file: 'logo.png', dark_file: 'dark.png', show_on: 'first' });
    expect(container.querySelector('.slide-logo')).toHaveAttribute(
      'src',
      expect.stringContaining('variant=light'),
    );
    await userEvent.click(screen.getByRole('button', { name: 'Dark' }));
    expect(container.querySelector('.slide-logo')).toHaveAttribute(
      'src',
      expect.stringContaining('variant=dark'),
    );
  });

  it('opens a slide full screen and steps through the slides', async () => {
    setup();
    await userEvent.click(screen.getByRole('button', { name: 'Full screen: Content' }));
    const dialog = screen.getByRole('dialog', { name: 'Full screen preview' });
    expect(within(dialog).getByText('2 / 5')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('Sample content slide')).toBeInTheDocument();

    await userEvent.click(within(dialog).getByRole('button', { name: 'Next slide' }));
    expect(within(dialog).getByText('3 / 5')).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Previous slide' }));
    await userEvent.click(within(dialog).getByRole('button', { name: 'Previous slide' }));
    expect(within(dialog).getByText('1 / 5')).toBeInTheDocument();
    expect(within(dialog).getByRole('button', { name: 'Previous slide' })).toBeDisabled();

    await userEvent.click(within(dialog).getByRole('button', { name: 'Close' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = setup({ file: 'logo.png' });
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe('FullScreen', () => {
  it('steps with the arrow keys and closes on a click outside', async () => {
    const onStep = vi.fn();
    const onClose = vi.fn();
    render(
      <FullScreen index={1} count={3} onStep={onStep} onClose={onClose}>
        <p>Custom content</p>
      </FullScreen>,
    );
    const dialog = screen.getByRole('dialog', { name: 'Full screen preview' });
    expect(dialog).toHaveAttribute('open');
    expect(screen.getByText('Custom content')).toBeInTheDocument();

    fireEvent.keyDown(dialog, { key: 'ArrowRight' });
    fireEvent.keyDown(dialog, { key: 'ArrowLeft' });
    expect(onStep.mock.calls).toEqual([[1], [-1]]);

    await userEvent.click(screen.getByText('Custom content'));
    expect(onClose).not.toHaveBeenCalled();
    await userEvent.click(dialog);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('disables the step that has nowhere to go', () => {
    const { rerender } = render(
      <FullScreen index={0} count={2} onStep={vi.fn()} onClose={vi.fn()}>
        <p>x</p>
      </FullScreen>,
    );
    expect(screen.getByRole('button', { name: 'Previous slide' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Next slide' })).toBeEnabled();
    rerender(
      <FullScreen index={1} count={2} onStep={vi.fn()} onClose={vi.fn()}>
        <p>x</p>
      </FullScreen>,
    );
    expect(screen.getByRole('button', { name: 'Next slide' })).toBeDisabled();
  });
});

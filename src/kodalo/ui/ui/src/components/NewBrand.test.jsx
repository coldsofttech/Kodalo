import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import NewBrand from './NewBrand.jsx';
import { PALETTES, typeInto } from '../testing.js';

const setup = (props = {}) => {
  const onCreate = vi.fn();
  const view = render(<NewBrand palettes={PALETTES} busy={false} onCreate={onCreate} {...props} />);
  return { onCreate, ...view };
};

describe('NewBrand', () => {
  it('offers every palette with Midnight chosen first', () => {
    setup();
    expect(screen.getAllByRole('radio').map((radio) => radio.nextSibling?.textContent)).toEqual([
      'Midnight',
      'Paper',
    ]);
    expect(screen.getByRole('radio', { name: /Midnight/ })).toBeChecked();
    expect(document.querySelectorAll('.swatch')).toHaveLength(PALETTES.length * 5);
  });

  it('needs a name before it can create a brand', async () => {
    const { onCreate } = setup();
    expect(screen.getByText('Create brand')).toHaveAttribute('disabled');
    await userEvent.click(screen.getByText('Create brand'));
    expect(onCreate).not.toHaveBeenCalled();

    typeInto(screen.getByLabelText('Brand name'), '  Acme  ');
    expect(screen.getByText('Create brand')).not.toHaveAttribute('disabled');
    await userEvent.click(screen.getByText('Create brand'));
    expect(onCreate).toHaveBeenCalledWith('Acme', 'system-midnight');
  });

  it('creates the brand from the palette that was picked', async () => {
    const { onCreate } = setup();
    typeInto(screen.getByLabelText('Brand name'), 'Acme');
    await userEvent.click(screen.getByRole('radio', { name: /Paper/ }));
    expect(screen.getByRole('radio', { name: /Paper/ })).toBeChecked();
    await userEvent.click(screen.getByText('Create brand'));
    expect(onCreate).toHaveBeenCalledWith('Acme', 'system-paper');
  });

  it('suggests a name on first run and submits with the form', () => {
    const { onCreate, container } = setup({ firstRun: true });
    expect(screen.getByLabelText('Brand name')).toHaveProperty('value', 'My brand');
    fireEvent.submit(/** @type {HTMLFormElement} */ (container.querySelector('form')));
    expect(onCreate).toHaveBeenCalledWith('My brand', 'system-midnight');
  });

  it('cannot create while busy', async () => {
    const { onCreate } = setup({ firstRun: true, busy: true });
    expect(screen.getByText('Create brand')).toHaveAttribute('disabled');
    await userEvent.click(screen.getByText('Create brand'));
    expect(onCreate).not.toHaveBeenCalled();
  });

  it('has no accessibility violations', async () => {
    const { container } = setup();
    expect(await axe(container)).toHaveNoViolations();
  });
});

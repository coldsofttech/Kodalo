import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ImportButton from './ImportButton.jsx';

const json = () => new File(['{}'], 'brand.json', { type: 'application/json' });

describe('ImportButton', () => {
  it('opens the file picker when the button is clicked', async () => {
    const open = vi.spyOn(HTMLInputElement.prototype, 'click');
    render(<ImportButton label="Import brand" what="brand" onImport={() => undefined} />);
    await userEvent.click(screen.getByLabelText('Import brand'));
    expect(open).toHaveBeenCalledTimes(1);
    open.mockRestore();
  });

  it('hands the chosen file over and clears the input for the next pick', async () => {
    const onImport = vi.fn();
    render(<ImportButton label="Import brand" what="brand" onImport={onImport} />);
    const input = /** @type {HTMLInputElement} */ (
      screen.getByLabelText('Choose a brand file to import')
    );
    const file = json();
    await userEvent.upload(input, file);
    expect(onImport).toHaveBeenCalledWith(file);
    expect(input.value).toBe('');
  });

  it('does not open the picker while disabled', async () => {
    const open = vi.spyOn(HTMLInputElement.prototype, 'click');
    render(<ImportButton label="Import brand" what="brand" disabled onImport={() => undefined} />);
    await userEvent.click(screen.getByLabelText('Import brand'));
    expect(open).not.toHaveBeenCalled();
    open.mockRestore();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <ImportButton label="Import layout" what="layout" onImport={() => undefined} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});

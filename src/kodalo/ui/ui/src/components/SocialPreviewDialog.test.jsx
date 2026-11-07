import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SocialPreviewDialog from './SocialPreviewDialog.jsx';
import { makeRepo } from '../testing.js';

const repo = makeRepo('coldsofttech');

describe('SocialPreviewDialog', () => {
  it('shows the repository social preview in an open dialog', () => {
    render(<SocialPreviewDialog repo={repo} onClose={() => undefined} />);
    expect(screen.getByRole('dialog', { name: 'Social preview' })).toHaveAttribute('open');
    const image = screen.getByRole('img', { name: 'Social preview of coldsofttech/repo' });
    expect(image).toHaveAttribute(
      'src',
      expect.stringContaining('/repositories/r1/social-preview'),
    );
  });

  it('closes from the close button, a click outside and the dialog close event', async () => {
    const onClose = vi.fn();
    render(<SocialPreviewDialog repo={repo} onClose={onClose} />);
    await userEvent.click(screen.getByRole('button', { name: 'Close' }));
    expect(onClose).toHaveBeenCalledTimes(1);

    await userEvent.click(screen.getByRole('dialog', { name: 'Social preview' }));
    expect(onClose).toHaveBeenCalledTimes(2);

    fireEvent(screen.getByRole('dialog', { name: 'Social preview' }), new Event('close'));
    expect(onClose).toHaveBeenCalledTimes(3);
  });

  it('stays open when the image itself is clicked', async () => {
    const onClose = vi.fn();
    render(<SocialPreviewDialog repo={repo} onClose={onClose} />);
    await userEvent.click(screen.getByRole('img'));
    expect(onClose).not.toHaveBeenCalled();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<SocialPreviewDialog repo={repo} onClose={() => undefined} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});

import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import HomePage from './Home.jsx';

describe('HomePage', () => {
  it('opens pages from its buttons and tiles', async () => {
    const onOpen = vi.fn();
    render(<HomePage onOpen={onOpen} />);
    await userEvent.click(screen.getByText('Open Studio'));
    await userEvent.click(screen.getByText('Manage brands'));
    await userEvent.click(screen.getByRole('button', { name: /Settings/ }));
    await userEvent.click(screen.getByRole('button', { name: /Add a repository/ }));
    expect(onOpen.mock.calls).toEqual([['studio'], ['brands'], ['settings'], ['repositories']]);
  });

  it('explains how it works in four steps', () => {
    render(<HomePage onOpen={() => undefined} />);
    expect(screen.getByRole('heading', { name: 'How it works' })).toBeInTheDocument();
    expect(screen.getAllByRole('listitem')).toHaveLength(7);
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<HomePage onOpen={() => undefined} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});

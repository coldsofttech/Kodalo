import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import HomePage from './Home.jsx';

describe('HomePage', () => {
  it('opens Studio and Brands from its buttons', async () => {
    const onOpen = vi.fn();
    render(<HomePage onOpen={onOpen} />);
    await userEvent.click(screen.getByText('Open Studio'));
    await userEvent.click(screen.getByText('Manage brands'));
    expect(onOpen.mock.calls).toEqual([['studio'], ['brands']]);
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<HomePage onOpen={() => undefined} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});

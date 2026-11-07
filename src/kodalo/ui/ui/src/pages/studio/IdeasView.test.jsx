import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import IdeasView from './IdeasView.jsx';

const IDEAS = {
  angles: [
    {
      id: 'angle-1',
      hooks: [
        { id: 'hook-1-1', text: 'Your disk is full of junk' },
        { id: 'hook-1-2', text: 'One command, gigabytes back' },
      ],
    },
    { id: 'angle-2', hooks: [{ id: 'hook-2-1', text: 'Stop guessing' }] },
  ],
  post_ideas: [
    {
      id: 'idea-1',
      angle_id: 'angle-1',
      hook_id: 'hook-1-1',
      format: 'carousel',
      working_title: 'Clean caches fast',
      objective: 'Show the speed',
      outline: ['The problem', 'The command'],
      visual_concept: 'A terminal',
      claims_used: [],
      risk_notes: '',
    },
    {
      id: 'idea-2',
      angle_id: 'angle-2',
      hook_id: 'hook-2-1',
      format: 'single_image',
      working_title: 'Stop guessing',
      objective: 'Show the report',
      outline: ['The report'],
      visual_concept: '',
      claims_used: [],
      risk_notes: '',
    },
  ],
  warnings: ['One claim was dropped.'],
};

const BRANDS = [
  { id: 'b1', name: 'Acme', is_default: true },
  { id: 'b2', name: 'Other', is_default: false },
];

const setup = (props = {}) => {
  const handlers = { onBrand: vi.fn(), onPick: vi.fn() };
  const view = render(
    <IdeasView ideas={IDEAS} brands={BRANDS} brandId="b1" pick={null} {...handlers} {...props} />,
  );
  return { ...handlers, ...view };
};

describe('IdeasView', () => {
  it('lists the post ideas with their format, objective and hook', () => {
    setup();
    const group = screen.getByRole('radiogroup', { name: 'Post ideas' });
    expect(within(group).getAllByRole('radio')).toHaveLength(2);
    expect(screen.getByText('Clean caches fast')).toBeInTheDocument();
    expect(screen.getByText('Carousel')).toBeInTheDocument();
    expect(screen.getByText('Single image')).toBeInTheDocument();
    expect(screen.getByText('Show the speed')).toBeInTheDocument();
    expect(screen.getByText('Hook: Your disk is full of junk')).toBeInTheDocument();
    expect(screen.getByText('One claim was dropped.')).toBeInTheDocument();
  });

  it('reports the idea that was chosen with its own hook', async () => {
    const { onPick } = setup();
    await userEvent.click(screen.getByRole('radio', { name: /Stop guessing/ }));
    expect(onPick).toHaveBeenCalledWith({ idea: 'idea-2', hook: 'hook-2-1' });
  });

  it('lets the chosen idea use another hook of its angle', async () => {
    const { onPick } = setup({ pick: { idea: 'idea-1', hook: 'hook-1-1' } });
    const hook = screen.getByLabelText('Hook');
    expect(hook).toHaveValue('hook-1-1');
    await userEvent.selectOptions(hook, 'hook-1-2');
    expect(onPick).toHaveBeenCalledWith({ idea: 'idea-1', hook: 'hook-1-2' });
  });

  it('shows the picked hook and no hook choice for an idea with a single hook', () => {
    setup({ pick: { idea: 'idea-1', hook: 'hook-1-2' } });
    expect(screen.getByText('Hook: One command, gigabytes back')).toBeInTheDocument();
    expect(screen.getAllByLabelText('Hook')).toHaveLength(1);
    setup({ pick: { idea: 'idea-2', hook: 'hook-2-1' } });
    expect(screen.getAllByLabelText('Hook')).toHaveLength(1);
  });

  it('shows the beats and visual of an idea in its details', async () => {
    setup();
    const [first] = screen.getAllByText('Details: beats and visual');
    await userEvent.click(first);
    expect(screen.getByText('The problem')).toBeVisible();
    expect(screen.getByText('The command')).toBeVisible();
    expect(screen.getByText('Visual: A terminal')).toBeVisible();
  });

  it('lets the brand be chosen, marking the default', async () => {
    const { onBrand } = setup();
    const select = screen.getByLabelText('Brand');
    expect(
      within(select)
        .getAllByRole('option')
        .map((o) => o.textContent),
    ).toEqual(['Acme (default)', 'Other']);
    await userEvent.selectOptions(select, 'b2');
    expect(onBrand).toHaveBeenCalledWith('b2');
  });

  it('asks for a brand when there is none', () => {
    setup({ brands: [] });
    expect(screen.queryByLabelText('Brand')).not.toBeInTheDocument();
    expect(screen.getByText(/No brand yet/)).toBeInTheDocument();
  });

  it('copies an idea as text with its hook', async () => {
    const user = userEvent.setup();
    setup();
    await user.click(screen.getAllByLabelText('Copy')[0]);
    expect(await screen.findByRole('status')).toHaveTextContent('Copied “Clean caches fast”.');
    const text = await navigator.clipboard.readText();
    expect(text).toContain('Clean caches fast (Carousel)');
    expect(text).toContain('Hook: Your disk is full of junk');
    expect(text).toContain('- The problem');
  });

  it('copies the hook that was picked', async () => {
    const user = userEvent.setup();
    setup({ pick: { idea: 'idea-1', hook: 'hook-1-2' } });
    await user.click(screen.getAllByLabelText('Copy')[0]);
    await screen.findByRole('status');
    expect(await navigator.clipboard.readText()).toContain('Hook: One command, gigabytes back');
  });

  it('says so when the text could not be copied', async () => {
    const user = userEvent.setup();
    setup();
    vi.spyOn(navigator.clipboard, 'writeText').mockRejectedValue(new Error('denied'));
    await user.click(screen.getAllByLabelText('Copy')[1]);
    expect(await screen.findByRole('status')).toHaveTextContent('The text could not be copied.');
  });

  it('explains when the AI found no ideas', () => {
    setup({ ideas: { ...IDEAS, post_ideas: [], warnings: [] } });
    expect(screen.getByText(/found nothing it could support/)).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Post ideas' })).not.toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = setup({ pick: { idea: 'idea-1', hook: 'hook-1-1' } });
    expect(await axe(container)).toHaveNoViolations();
  });
});

import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import FocusView from './FocusView.jsx';

const README = {
  features: [
    { name: 'Dry run', importance: 'minor', maturity: 'stable', claims: [] },
    {
      name: 'Scan',
      importance: 'headline',
      maturity: 'experimental',
      claims: [{ text: 'Finds every cache' }, { text: 'Never deletes by itself' }],
    },
    { name: 'Report', importance: 'supporting', maturity: 'stable', claims: [] },
  ],
  use_cases: [{ title: 'Free disk space' }],
  capabilities: [{ name: 'Runs offline' }],
};

const setup = (props = {}) => {
  const handlers = { onChange: vi.fn(), onFocus: vi.fn() };
  const view = render(
    <FocusView postType="tool" readme={README} focus="" {...handlers} {...props} />,
  );
  return { ...handlers, ...view };
};

describe('FocusView', () => {
  it('offers the two kinds of post and reports the one chosen', async () => {
    const { onChange } = setup();
    const group = screen.getByRole('radiogroup', { name: 'Post type' });
    expect(within(group).getAllByRole('radio')).toHaveLength(2);
    expect(screen.getByRole('radio', { name: /Tool \/ Utility post/ })).toBeChecked();
    await userEvent.click(screen.getByRole('radio', { name: /Feature post/ }));
    expect(onChange).toHaveBeenCalledWith('feature');
  });

  it('has nothing to choose for a tool post', () => {
    setup();
    expect(screen.queryByLabelText('Focus on')).not.toBeInTheDocument();
  });

  it('lists features, use cases and capabilities for a feature post, headline features first', () => {
    setup({ postType: 'feature' });
    const select = screen.getByLabelText('Focus on');
    expect(
      within(select)
        .getAllByRole('group')
        .map((group) => group.getAttribute('label')),
    ).toEqual(['Features', 'Use cases', 'Capabilities']);
    expect(
      within(select)
        .getAllByRole('option')
        .map((option) => option.textContent),
    ).toEqual([
      'Choose a feature, use case or capability',
      'Scan',
      'Report',
      'Dry run',
      'Free disk space',
      'Runs offline',
    ]);
  });

  it('reports the focus that was picked', async () => {
    const { onFocus } = setup({ postType: 'feature' });
    await userEvent.selectOptions(screen.getByLabelText('Focus on'), 'use_cases:0');
    expect(onFocus).toHaveBeenCalledWith('use_cases:0');
  });

  it('leaves out the groups that are empty', () => {
    setup({ postType: 'feature', readme: { features: [], use_cases: [{ title: 'Only one' }] } });
    const select = screen.getByLabelText('Focus on');
    expect(within(select).getAllByRole('group')).toHaveLength(1);
  });

  it('points to Analyze when there is nothing to focus on', () => {
    setup({ postType: 'feature', readme: { features: [], use_cases: [], capabilities: [] } });
    expect(screen.queryByLabelText('Focus on')).not.toBeInTheDocument();
    expect(screen.getByText(/Nothing was found to focus on/)).toBeInTheDocument();
  });

  it('warns about a feature that is experimental or has claims to repeat with care', () => {
    setup({ postType: 'feature', focus: 'features:1' });
    expect(screen.getByText('The documents call this experimental.')).toBeInTheDocument();
    expect(
      screen.getByText('Repeat with care: Finds every cache; Never deletes by itself.'),
    ).toBeInTheDocument();
  });

  it('shows no warning for a stable feature or another kind of focus', () => {
    const { unmount } = setup({ postType: 'feature', focus: 'features:0' });
    expect(screen.queryByText(/documents call this/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Repeat with care/)).not.toBeInTheDocument();
    unmount();
    setup({ postType: 'feature', focus: 'capabilities:0' });
    expect(screen.queryByText(/Repeat with care/)).not.toBeInTheDocument();
  });

  it('copes with a README that was not read', () => {
    setup({ postType: 'feature', readme: null });
    expect(screen.getByText(/Nothing was found to focus on/)).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = setup({ postType: 'feature', focus: 'features:1' });
    expect(await axe(container)).toHaveNoViolations();
  });
});

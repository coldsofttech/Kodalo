import { afterEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Platforms from './Platforms.jsx';
import { createBackend, mockApi, setChecked, typeInto } from '../../testing.js';

afterEach(() => vi.unstubAllGlobals());

describe('Platforms', () => {
  it('shows the Instagram defaults and saves the hashtag settings', async () => {
    const calls = mockApi(createBackend([]).handler);
    const { container } = render(<Platforms />);

    expect(await screen.findByLabelText('Platform')).toHaveProperty('value', 'instagram');
    expect(screen.getByLabelText('Hashtags per post')).toBeInTheDocument();

    typeInto(screen.getByLabelText('Default hashtags'), '#Sweepito, #tools');
    expect(screen.getByLabelText('Use icons')).toHaveProperty('checked', false);
    setChecked(screen.getByLabelText('Use social preview'), true);
    setChecked(screen.getByLabelText('Build custom images as needed'), true);
    await userEvent.click(screen.getByLabelText('Save'));

    expect(await screen.findByText('Saved.')).toBeInTheDocument();
    expect(calls.findLast((call) => call.method === 'PUT').body).toEqual({
      hashtag_count: 5,
      default_hashtags: ['#Sweepito', '#tools'],
      use_social_preview: true,
      use_repo_icon: false,
      use_icons: false,
      build_custom_images: true,
      use_ai_templates: false,
    });
    expect(await axe(container)).toHaveNoViolations();
  });

  it('shows what is saved when it opens, and a failed save is shown', async () => {
    const backend = createBackend([]);
    mockApi(backend.handler);
    const first = render(<Platforms />);
    typeInto(await screen.findByLabelText('Default hashtags'), '#one');
    await userEvent.click(screen.getByLabelText('Save'));
    await screen.findByText('Saved.');
    first.unmount();

    render(<Platforms />);
    await vi.waitFor(() =>
      expect(screen.getByLabelText('Default hashtags')).toHaveProperty('value', '#one'),
    );
  });
});

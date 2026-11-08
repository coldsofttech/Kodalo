import { afterEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DesignView from './DesignView.jsx';
import { createBackend, makeBrand, makeRepo, mockApi } from '../../testing.js';

afterEach(() => vi.unstubAllGlobals());

const brand = makeBrand('b1', 'My Brand', true);

const copy = {
  platform: 'instagram',
  idea_id: 'idea-1',
  hook_id: 'hook-1',
  hook_text: 'Hook',
  format: 'carousel',
  slides: [
    { role: 'hook', headline: 'What if?', body: '', visual_note: '', alt_text: 'A timeline' },
    { role: 'step', headline: 'Run a hook', body: 'After commits.', visual_note: '', alt_text: '' },
  ],
  caption: { opening: 'Opening line', body: ['First line'], cta: 'Read the docs.' },
  alt_opening: { text: 'Other', hook_id: '' },
  hashtags: ['#sweepito'],
  review_flags: [],
  warnings: [],
  input_tokens: 1,
  output_tokens: 1,
};

const slide = (changes) => ({
  template: 'step',
  align: 'left',
  media: 'none',
  accent: 'primary',
  icon: '',
  image_source: 'none',
  image_fit: 'cover',
  has_svg: false,
  has_html: false,
  ...changes,
});

const design = {
  platform: 'instagram',
  idea_id: 'idea-1',
  hook_id: 'hook-1',
  slides: [
    slide({ template: 'hook', align: 'center', icon: 'git' }),
    slide({ media: 'top', image_source: 'social_preview' }),
  ],
  logo_box: null,
  warnings: ['Slide 2: the drawing was not allowed or not safe.'],
  input_tokens: 10,
  output_tokens: 20,
};

const request = { brand_id: 'b1', post_type: 'tool', kind: '', name: '', idea_id: 'idea-1' };
const repo = { ...makeRepo('o'), has_social_preview: true };

function show(overrides = {}, shown = brand) {
  mockApi(createBackend([]).handler);
  return render(
    <DesignView
      design={{ ...design, ...overrides }}
      copy={copy}
      brand={shown}
      repo={repo}
      request={{ ...request, hook_id: '' }}
    />,
  );
}

describe('DesignView', () => {
  it('shows every slide as a page in a frame, then the caption and the hashtags', async () => {
    const { container } = show();

    expect(screen.getByRole('heading', { name: 'Slides' })).toBeVisible();
    expect(screen.getByTitle('Slide 1').tagName).toBe('IFRAME');
    expect(screen.getByTitle('Slide 2').tagName).toBe('IFRAME');
    expect(screen.getByRole('region', { name: 'Caption' })).toHaveTextContent('Opening line');
    expect(screen.getByRole('list', { name: 'Hashtags' })).toHaveTextContent('#sweepito');
    expect(screen.getByText(/drawing was not allowed/)).toBeVisible();
    // jsdom cannot run axe inside frames; the slide pages are checked as pages on the server.
    expect(await axe(container, { iframes: false })).toHaveNoViolations();
  });

  it('opens a slide full screen and steps through them', async () => {
    show();

    await userEvent.click(screen.getByLabelText('Full screen: Slide 1'));
    const dialog = screen.getByLabelText('Full screen preview');
    expect(dialog).toHaveTextContent('1 / 2');

    await userEvent.click(screen.getByLabelText('Next slide'));
    expect(dialog).toHaveTextContent('2 / 2');
    await userEvent.click(screen.getByLabelText('Close'));
    expect(screen.queryByLabelText('Full screen preview')).not.toBeInTheDocument();
  });

  it('shows each slide in a frame that can run nothing, in the chosen mode', async () => {
    show();

    const frame = screen.getByTitle('Slide 1');
    expect(frame).toHaveAttribute('sandbox', '');
    expect(frame.getAttribute('src')).toContain('/design/slide?');
    expect(frame.getAttribute('src')).toContain('slide=0');
    expect(frame.getAttribute('src')).toContain('mode=light');
    expect(screen.getByTitle('Slide 2').getAttribute('src')).toContain('slide=1');

    await userEvent.click(screen.getByRole('button', { name: 'Dark' }));
    expect(screen.getByTitle('Slide 1').getAttribute('src')).toContain('mode=dark');
  });

  it('offers Export above the slides for an Instagram canvas and hides it for a custom one', async () => {
    const custom = { ...brand, canvas: { ...brand.canvas, platform_id: 'custom' } };
    const first = show();
    const exportButton = await screen.findByLabelText('Export slides and caption');
    const heading = screen.getByRole('heading', { name: 'Slides' });
    expect(exportButton.closest('.post-title-row')).toContainElement(heading);
    expect(exportButton).toHaveTextContent('');
    // Post only appears once Instagram is connected.
    expect(screen.queryByLabelText('Post to Instagram')).not.toBeInTheDocument();
    first.unmount();

    show({}, custom);
    expect(await screen.findByRole('region', { name: 'Caption' })).toBeVisible();
    expect(screen.queryByLabelText('Export slides and caption')).not.toBeInTheDocument();
  });
});

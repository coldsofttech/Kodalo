import { describe, expect, it } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DesignView from './DesignView.jsx';
import { makeBrand, makeRepo } from '../../testing.js';

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

function show(overrides = {}) {
  return render(
    <DesignView
      design={{ ...design, ...overrides }}
      copy={copy}
      brand={brand}
      repo={repo}
      request={{ ...request, hook_id: '' }}
    />,
  );
}

describe('DesignView', () => {
  it('draws each slide with its own text, then the caption and the hashtags', async () => {
    const { container } = show();

    expect(screen.getByRole('heading', { name: 'Slides' })).toBeVisible();
    expect(screen.getByRole('article', { name: 'Slide 1' })).toHaveTextContent('What if?');
    expect(screen.getByRole('article', { name: 'Slide 2' })).toHaveTextContent('Run a hook');
    expect(screen.getByRole('article', { name: 'Slide 2' })).toHaveTextContent('After commits.');
    expect(screen.getByRole('img', { name: 'Slide 2 picture' })).toHaveAttribute(
      'src',
      expect.stringContaining('/social-preview'),
    );
    expect(container.querySelector('.bi-git')).not.toBeNull();
    expect(screen.getByRole('region', { name: 'Caption' })).toHaveTextContent('Opening line');
    expect(screen.getByRole('list', { name: 'Hashtags' })).toHaveTextContent('#sweepito');
    expect(screen.getByText(/drawing was not allowed/)).toBeVisible();
    expect(await axe(container)).toHaveNoViolations();
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

  it('shows the repository icon, or the logo cut from the preview', () => {
    show({
      slides: [
        slide({ media: 'top', image_source: 'repo_icon' }),
        slide({ media: 'top', image_source: 'repo_icon' }),
      ],
      logo_box: { x: 0.1, y: 0.1, w: 0.3, h: 0.3 },
    });

    expect(screen.getAllByRole('img', { name: /picture|timeline/ })).toHaveLength(2);
  });

  it('shows an AI-written slide in a frame that can run nothing, in the chosen mode', async () => {
    show({ slides: [slide({ has_html: true }), slide()] });

    const frame = screen.getByTitle('Slide 1');
    expect(frame.tagName).toBe('IFRAME');
    expect(frame).toHaveAttribute('sandbox', '');
    expect(frame.getAttribute('src')).toContain('/design/slide?');
    expect(frame.getAttribute('src')).toContain('slide=0');
    expect(frame.getAttribute('src')).toContain('mode=light');
    expect(screen.getByRole('article', { name: 'Slide 2' })).toBeVisible();

    await userEvent.click(screen.getByRole('button', { name: 'Dark' }));
    expect(screen.getByTitle('Slide 1').getAttribute('src')).toContain('mode=dark');
  });
});

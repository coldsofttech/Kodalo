import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PostView from './PostView.jsx';
import { typeInto, clickWhenReady } from '../../testing.js';

const URL = 'https://github.com/o/r';
const COPY = {
  platform: 'instagram',
  idea_id: 'idea-1',
  hook_id: 'hook-1-1',
  hook_text: 'What if cleanup ran after each commit?',
  format: 'carousel',
  slides: [
    {
      role: 'hook',
      headline: 'What if cleanup ran after each commit?',
      body: '',
      visual_note: 'A commit timeline',
      alt_text: 'A timeline of commits',
    },
    { role: 'cta', headline: 'Read the docs', body: 'Set it up.', visual_note: '', alt_text: '' },
  ],
  caption: { opening: 'Opening line', body: ['One', 'Two'], cta: 'Read the docs.', repo_url: URL },
  alt_opening: { text: 'Another opening', hook_id: 'hook-1-2' },
  hashtags: ['#sweepito', '#git'],
  review_flags: [{ type: 'needs_review', text: 'Runs after commits', reason: 'Check it' }],
  warnings: [],
  input_tokens: 1,
  output_tokens: 2,
};

const NEW_LINES = ['First', '', ' Second '].join('\n');

describe('PostView', () => {
  it('lists the slides and the caption as collapsible items that read as text', async () => {
    const { container } = render(<PostView copy={COPY} busy={false} onSave={() => undefined} />);

    expect(screen.getByRole('heading', { name: 'Slides' })).toBeVisible();
    expect(screen.getByText('Slide 1')).toBeVisible();
    expect(screen.getByText('Slide 2')).toBeVisible();
    expect(screen.getByText('Caption')).toBeVisible();
    expect(screen.getByText('#sweepito')).toBeInTheDocument();
    expect(screen.queryByText(/Check:/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Slide 1 headline')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Save changes')).not.toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('shows fields while one item is edited and saves the text as edited', async () => {
    const save = vi.fn();
    const { container } = render(<PostView copy={COPY} busy={false} onSave={save} />);

    await userEvent.click(screen.getByLabelText('Edit Slide 2'));
    await waitFor(() =>
      expect(screen.getByLabelText('Slide 2 headline')).toHaveValue('Read the docs'),
    );
    expect(screen.getByLabelText('Edit caption')).toHaveAttribute('disabled');
    expect(screen.getByLabelText('Save changes')).toHaveAttribute('disabled');
    expect(await axe(container)).toHaveNoViolations();

    typeInto(screen.getByLabelText('Slide 2 headline'), 'Read the guide');
    await clickWhenReady(screen.getByLabelText('Save changes'));

    expect(save).toHaveBeenCalledWith({
      slides: [COPY.slides[0], { ...COPY.slides[1], headline: 'Read the guide' }],
      caption: {
        opening: 'Opening line',
        body: ['One', 'Two'],
        cta: 'Read the docs.',
        repo_url: URL,
      },
      alt_opening: 'Another opening',
      hashtags: ['#sweepito', '#git'],
    });
  });

  it('edits the caption and its hashtags together', async () => {
    const save = vi.fn();
    render(<PostView copy={COPY} busy={false} onSave={save} />);

    await userEvent.click(screen.getByLabelText('Edit caption'));
    await waitFor(() => expect(screen.getByLabelText('Hashtags')).toHaveValue('#sweepito #git'));
    typeInto(screen.getByLabelText('Caption text'), NEW_LINES);
    await waitFor(() => expect(screen.getByLabelText('Repo URL')).toHaveValue(URL));
    typeInto(screen.getByLabelText('Hashtags'), '#a, #b');
    await clickWhenReady(screen.getByLabelText('Save changes'));

    expect(save).toHaveBeenCalledWith({
      slides: COPY.slides,
      caption: {
        opening: 'Opening line',
        body: ['First', 'Second'],
        cta: 'Read the docs.',
        repo_url: URL,
      },
      alt_opening: 'Another opening',
      hashtags: ['#a', '#b'],
    });
  });

  it('drops the edits on Cancel', async () => {
    render(<PostView copy={COPY} busy={false} onSave={() => undefined} />);

    await userEvent.click(screen.getByLabelText('Edit Slide 1'));
    typeInto(screen.getByLabelText('Slide 1 headline'), 'Changed');
    await clickWhenReady(screen.getByLabelText('Cancel'));

    expect(screen.queryByLabelText('Slide 1 headline')).not.toBeInTheDocument();
    expect(screen.queryByText('Changed')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Edit Slide 1')).not.toHaveAttribute('disabled');
  });

  it('calls a single image the image text', () => {
    render(
      <PostView
        copy={{ ...COPY, format: 'single_image', slides: [COPY.slides[0]] }}
        busy={false}
        onSave={() => undefined}
      />,
    );

    expect(screen.getByRole('heading', { name: 'Image text' })).toBeVisible();
    expect(screen.getByLabelText('Edit Image')).toBeInTheDocument();
  });
});

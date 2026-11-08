import { describe, expect, it } from 'vitest';
import { ideaText } from './ideas.js';

const FULL = {
  working_title: 'Ship faster',
  format: 'carousel',
  objective: 'Show the CLI',
  outline: ['Install it', 'Run it'],
  visual_concept: 'A terminal',
  claims_used: [{ text: 'It is fast', file: 'README.md', quote: 'very fast' }],
  risk_notes: 'Check the numbers',
};

describe('ideaText', () => {
  it('writes every part of the idea', () => {
    expect(ideaText(FULL, 'Stop waiting')).toBe(
      [
        'Ship faster (Carousel)',
        'Hook: Stop waiting',
        'Objective: Show the CLI',
        '',
        '- Install it',
        '- Run it',
        '',
        'Visual: A terminal',
        '',
        'Claims and sources:',
        '- It is fast (README.md: "very fast")',
        '',
        'Careful: Check the numbers',
      ].join('\n'),
    );
  });

  it('leaves out what the idea does not have', () => {
    const bare = {
      working_title: 'One',
      format: 'single',
      objective: '',
      outline: [],
      visual_concept: '',
      claims_used: [],
      risk_notes: '',
    };

    expect(ideaText(bare, '')).toBe('One (Single image)');
  });
});

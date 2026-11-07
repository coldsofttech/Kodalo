import { describe, expect, it } from 'vitest';
import { languageColor } from './languageColors.js';

describe('languageColor', () => {
  it('returns the color GitHub uses for a known language', () => {
    expect(languageColor('Python')).toBe('#3572A5');
    expect(languageColor('C++')).toBe('#f34b7d');
  });

  it('gives an unknown language a steady color of its own', () => {
    const color = languageColor('Zig');
    expect(color).toMatch(/^#[0-9a-f]{6}$/i);
    expect(languageColor('Zig')).toBe(color);
  });

  it('copes with an empty name', () => {
    expect(languageColor('')).toMatch(/^#[0-9a-f]{6}$/i);
  });
});

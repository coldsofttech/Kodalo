import { describe, expect, it } from 'vitest';
import { HEX, logoFor, previewVariables, sameData, setIn } from './brand.js';
import { LAYOUTS, SAMPLE_DATA } from '../testing.js';

describe('setIn', () => {
  it('replaces a nested value without changing the original', () => {
    const data = SAMPLE_DATA();
    const changed = setIn(data, 'colors.primary.light', '#000000');
    expect(changed.colors.primary.light).toBe('#000000');
    expect(changed.colors.primary.dark).toBe(data.colors.primary.dark);
    expect(data.colors.primary.light).toBe('#2563eb');
  });
});

describe('sameData', () => {
  it('compares by value', () => {
    expect(sameData(SAMPLE_DATA(), SAMPLE_DATA())).toBe(true);
    expect(sameData(SAMPLE_DATA(), setIn(SAMPLE_DATA(), 'layout.align', 'center'))).toBe(false);
  });
});

describe('HEX', () => {
  it('accepts six hex digits only', () => {
    expect(HEX.test('#2563EB')).toBe(true);
    for (const bad of ['2563eb', '#fff', '#12345g', '#1234567', 'red']) {
      expect(HEX.test(bad)).toBe(false);
    }
  });
});

const CANVAS = { width: 1080, height: 1350 };
const LAYOUT = LAYOUTS[0];

describe('previewVariables', () => {
  it('maps colors for the chosen mode', () => {
    const light = previewVariables(SAMPLE_DATA(), 'light', LAYOUT, CANVAS);
    const dark = previewVariables(SAMPLE_DATA(), 'dark', LAYOUT, CANVAS);
    expect(light['--b-background']).toBe('#ffffff');
    expect(dark['--b-background']).toBe('#0b1020');
    expect(light['--b-primary-alt']).toBe('#1d4ed8');
  });

  it('maps fonts, layout and logo settings', () => {
    const vars = previewVariables(SAMPLE_DATA(), 'light', LAYOUT, CANVAS);
    expect(vars['--f-heading']).toBe('"Poppins", sans-serif');
    expect(vars['--f-mono-alt']).toBe('"Fira Code", monospace');
    expect(vars['--canvas-w']).toBe('1080');
    expect(vars['--canvas-h']).toBe('1350');
    expect(vars['--m-side']).toBe('80');
    expect(vars['--gap']).toBe('30');
    expect(vars['--logo-size']).toBe('14');
  });

  it('follows density', () => {
    const spacious = { ...LAYOUT, density: 'spacious' };
    expect(previewVariables(SAMPLE_DATA(), 'light', spacious, CANVAS)['--gap']).toBe('46');
  });
});

describe('logoFor', () => {
  it('uses the dark logo in dark mode only when there is one', () => {
    const none = SAMPLE_DATA();
    expect(logoFor(none, 'light').present).toBe(false);
    const main = setIn(none, 'logo.file', 'a.png');
    expect(logoFor(main, 'dark')).toEqual({ variant: 'light', present: true });
    const both = setIn(main, 'logo.dark_file', 'b.png');
    expect(logoFor(both, 'dark')).toEqual({ variant: 'dark', present: true });
    expect(logoFor(both, 'light')).toEqual({ variant: 'light', present: true });
  });
});

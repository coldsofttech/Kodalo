// What a brand profile looks like to the page, and how it becomes CSS for the live preview.
// The CSS variable names below are the one place the preview reads brand data; the slide designer
// in Python must map the same fields the same way.

import { get } from './lookup.js';

/** Colors in the order they are edited: label, key and what the color is used for. */
export const COLOR_ROWS = [
  ['Background', 'background', 'Slide background'],
  ['Primary', 'primary', 'Headings and buttons'],
  ['Secondary', 'secondary', 'Supporting accents'],
  ['Text', 'text', 'Body text'],
  ['Background (alternative)', 'background_alt', 'Callouts and highlighted slides'],
  ['Primary (alternative)', 'primary_alt', 'Emphasis inside a slide'],
  ['Secondary (alternative)', 'secondary_alt', 'Second emphasis inside a slide'],
  ['Text (alternative)', 'text_alt', 'Text on alternative backgrounds'],
];

/** Fonts: label, key, and the generic family used when the font is not installed. */
export const FONT_ROWS = [
  ['Heading', 'heading', 'sans-serif'],
  ['Heading (alternative)', 'heading_alt', 'sans-serif'],
  ['Body', 'body', 'sans-serif'],
  ['Body (alternative)', 'body_alt', 'sans-serif'],
  ['Monospace', 'mono', 'monospace'],
  ['Monospace (alternative)', 'mono_alt', 'monospace'],
];

export const LOGO_POSITIONS = [
  ['top_left', 'Top left'],
  ['top_center', 'Top center'],
  ['top_right', 'Top right'],
  ['bottom_left', 'Bottom left'],
  ['bottom_center', 'Bottom center'],
  ['bottom_right', 'Bottom right'],
];

/** The hex pattern the API accepts. */
export const HEX = /^#[0-9a-f]{6}$/i;

/**
 * Return a copy of `object` with the value at the dotted `path` replaced.
 * @template T
 * @param {T} object
 * @param {string} path
 * @param {unknown} value
 * @returns {T}
 */
export function setIn(object, path, value) {
  const [head, ...rest] = path.split('.');
  const source = /** @type {Record<string, unknown>} */ (object);
  return /** @type {T} */ ({
    ...source,
    [head]: rest.length ? setIn(get(source, head), rest.join('.'), value) : value,
  });
}

/** @param {unknown} a @param {unknown} b */
export const sameData = (a, b) => JSON.stringify(a) === JSON.stringify(b);

/** @param {{ family: string }} font @param {string} generic */
export const fontStack = (font, generic) => `"${font.family}", ${generic}`;

/**
 * CSS custom properties for the preview. Lengths are in canvas pixels; the slide scales them with
 * its container width, so every slide keeps the proportions of the real canvas at any size.
 * @param {any} data brand data
 * @param {'light' | 'dark'} mode
 * @param {any} layout the layout the brand uses (margins, corner radius, text, slide count)
 * @param {{ width: number, height: number }} canvas the canvas of that layout
 * @returns {Record<string, string>}
 */
export function previewVariables(data, mode, layout, canvas) {
  const { colors, fonts } = data;
  /** @type {Record<string, string>} */
  const vars = {
    '--canvas-w': String(canvas.width),
    '--canvas-h': String(canvas.height),
    '--m-top': String(layout.margin_top),
    '--m-side': String(layout.margin_side),
    '--m-bottom': String(layout.margin_bottom),
    '--radius': String(layout.corner_radius),
    '--align': layout.align,
    '--logo-size': String(data.logo.size_percent),
    '--logo-pad': String(data.logo.padding),
    '--gap': String(
      { compact: 18, regular: 30, spacious: 46 }[/** @type {'regular'} */ (layout.density)] ?? 30,
    ),
  };
  for (const [, key] of COLOR_ROWS) {
    vars[`--b-${key.replace('_', '-')}`] = get(get(colors, key), mode);
  }
  for (const [, key, generic] of FONT_ROWS) {
    vars[`--f-${key.replace('_', '-')}`] = fontStack(get(fonts, key), generic);
  }
  return vars;
}

/** Which logo file shows in a mode: the dark one if there is one, else the main one. */
export function logoFor(/** @type {any} */ data, /** @type {'light' | 'dark'} */ mode) {
  const { file, dark_file: darkFile } = data.logo;
  if (mode === 'dark' && darkFile) return { variant: 'dark', present: true };
  return { variant: 'light', present: Boolean(file) };
}

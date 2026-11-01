// Browser helpers for files: saving a JSON document and reading one the user picked.
// They never talk to Python, so they live apart from api.js.

/**
 * Offer `document` to the user as a downloaded JSON file.
 * @param {object} document_
 * @param {string} filename
 */
export function saveJson(document_, filename) {
  const blob = new Blob([JSON.stringify(document_, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

/**
 * Read a picked file as JSON.
 * @param {File} file
 * @returns {Promise<unknown>}
 */
export async function readJson(file) {
  return JSON.parse(await file.text());
}

/** A file name that is safe on Windows. @param {string} name */
export function fileNameFor(name) {
  const cleaned = name.replace(/[^\w .-]+/g, '').trim();
  return `${cleaned || 'brand'}.kodalo-brand.json`;
}

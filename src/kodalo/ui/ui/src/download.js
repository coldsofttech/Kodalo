// Browser helpers for files: saving a JSON document and reading one the user picked.
// Saving goes through the window's save dialog (api.js) and falls back to a browser download.
import { saveJsonFile } from './api.js';

/**
 * Let the user choose where to save `document_` as a JSON file.
 * @param {object} document_
 * @param {string} filename
 * @returns {Promise<boolean>} false when the user cancelled the dialog
 */
export async function saveJson(document_, filename) {
  return saveText(JSON.stringify(document_, null, 2), filename, {
    mime: 'application/json',
    label: 'JSON files (*.json)',
  });
}

/**
 * Let the user choose where to save `text`.
 * @param {string} text
 * @param {string} filename
 * @param {{ mime: string, label: string }} type the media type and the save dialog's filter
 * @returns {Promise<boolean>} false when the user cancelled the dialog
 */
export async function saveText(text, filename, type) {
  let outcome = 'unavailable';
  try {
    outcome = await saveJsonFile(filename, text, type.label);
  } catch (failure) {
    // A page opened in a browser has no bridge; any other failure is the user's to see.
    if (!(failure instanceof TypeError)) throw failure;
  }
  if (outcome !== 'unavailable') return outcome === 'saved';
  const url = URL.createObjectURL(new Blob([text], { type: type.mime }));
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
  return true;
}

/**
 * Read a picked file as JSON.
 * @param {File} file
 * @returns {Promise<unknown>}
 */
export async function readJson(file) {
  return JSON.parse(await file.text());
}

/**
 * A file name that is safe on Windows.
 * @param {string} name
 * @param {string} [kind] what the file holds: brand, canvas, palette or layout
 */
export function fileNameFor(name, kind = 'brand') {
  const cleaned = name.replace(/[^\w .-]+/g, '').trim();
  return `${cleaned || kind}.kodalo-${kind}.json`;
}

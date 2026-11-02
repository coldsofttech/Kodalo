// Every call to Python lives here. Cornea serves the page and the API from one address, so paths
// are relative and the session cookie is sent automatically.

/** A failed call, with a message that is safe to show to the user. */
export class ApiError extends Error {
  /**
   * @param {string} message
   * @param {number} status
   */
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

/** @param {unknown} body @param {number} status */
function messageFor(body, status) {
  if (body && typeof body === 'object') {
    const { detail, errors } = /** @type {Record<string, unknown>} */ (body);
    if (Array.isArray(errors) && errors.length > 0) {
      const first = errors[0];
      const where = Array.isArray(first?.loc) ? first.loc.slice(1).join('.') : '';
      return where ? `${where}: ${first.msg}` : String(first?.msg ?? detail);
    }
    if (typeof detail === 'string') return detail;
  }
  return `Something went wrong (${status}).`;
}

/**
 * @param {string} path
 * @param {RequestInit & { json?: unknown }} [options]
 */
async function request(path, { json, headers, ...options } = {}) {
  /** @type {Record<string, string>} */
  const sent = { ...headers };
  let body = options.body;
  if (json !== undefined) {
    sent['Content-Type'] = 'application/json';
    body = JSON.stringify(json);
  }
  let response;
  try {
    response = await fetch(path, { ...options, headers: sent, body });
  } catch {
    throw new ApiError('Kodalo could not be reached.', 0);
  }
  if (response.status === 204) return null;
  /** @type {unknown} */
  const parsed = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(messageFor(parsed, response.status), response.status);
  return parsed;
}

const BRANDS = '/api/v1/brands';

export const listBrands = () => request(BRANDS);
/** @param {{ name: string, palette?: string, data?: object }} body */
export const createBrand = (body) => request(BRANDS, { method: 'POST', json: body });
/** @param {string} id @param {{ name?: string, data?: object }} body */
export const updateBrand = (id, body) =>
  request(`${BRANDS}/${id}`, { method: 'PATCH', json: body });
/** @param {string} id */
export const deleteBrand = (id) => request(`${BRANDS}/${id}`, { method: 'DELETE' });
/** @param {string} id */
export const setDefaultBrand = (id) => request(`${BRANDS}/${id}/default`, { method: 'POST' });
/** @param {string} id @param {string} name */
export const duplicateBrand = (id, name) =>
  request(`${BRANDS}/${id}/duplicate`, { method: 'POST', json: { name } });
/** @param {string} id */
export const exportBrand = (id) => request(`${BRANDS}/${id}/export`);
/** @param {object} document @param {string} [name] */
export const importBrand = (document, name) =>
  request(`${BRANDS}/import${name ? `?name=${encodeURIComponent(name)}` : ''}`, {
    method: 'POST',
    json: document,
  });
/** @param {object} colors */
export const checkContrast = (colors) =>
  request(`${BRANDS}/contrast`, { method: 'POST', json: { colors } });

/**
 * @param {string} id
 * @param {File} file PNG or SVG
 * @param {'light' | 'dark'} variant
 */
export const uploadLogo = (id, file, variant) =>
  request(`${BRANDS}/${id}/logo?variant=${variant}`, {
    method: 'PUT',
    headers: { 'Content-Type': file.type },
    body: file,
  });
/** @param {string} id @param {'light' | 'dark'} variant */
export const removeLogo = (id, variant) =>
  request(`${BRANDS}/${id}/logo?variant=${variant}`, { method: 'DELETE' });
/** Address of a stored logo, changing whenever the profile changes so the browser reloads it. */
export const logoUrl = (
  /** @type {string} */ id,
  /** @type {'light' | 'dark'} */ variant,
  /** @type {string} */ version,
) => `${BRANDS}/${id}/logo?variant=${variant}&v=${encodeURIComponent(version)}`;

const PALETTES = '/api/v1/palettes';

export const listPalettes = () => request(PALETTES);
/** @param {{ name: string, colors: object }} body */
export const createPalette = (body) => request(PALETTES, { method: 'POST', json: body });
/** @param {string} id @param {{ name?: string, colors?: object }} body */
export const updatePalette = (id, body) =>
  request(`${PALETTES}/${id}`, { method: 'PATCH', json: body });
/** @param {string} id @param {string} name */
export const duplicatePalette = (id, name) =>
  request(`${PALETTES}/${id}/duplicate`, { method: 'POST', json: { name } });
/** @param {string} id */
export const deletePalette = (id) => request(`${PALETTES}/${id}`, { method: 'DELETE' });
/** @param {string} id */
export const exportPalette = (id) => request(`${PALETTES}/${id}/export`);
/** @param {object} body @param {string} [name] */
export const importPalette = (body, name) =>
  request(`${PALETTES}/import${name ? `?name=${encodeURIComponent(name)}` : ''}`, {
    method: 'POST',
    json: body,
  });

const LAYOUTS = '/api/v1/layouts';

export const listLayouts = () => request(LAYOUTS);
/** @param {{ name: string, settings?: object }} body */
export const createLayout = (body) => request(LAYOUTS, { method: 'POST', json: body });
/** @param {string} id @param {Record<string, unknown>} body */
export const updateLayout = (id, body) =>
  request(`${LAYOUTS}/${id}`, { method: 'PATCH', json: body });
/** @param {string} id @param {string} name */
export const duplicateLayout = (id, name) =>
  request(`${LAYOUTS}/${id}/duplicate`, { method: 'POST', json: { name } });
/** @param {string} id */
export const deleteLayout = (id) => request(`${LAYOUTS}/${id}`, { method: 'DELETE' });
/** @param {string} id */
export const exportLayout = (id) => request(`${LAYOUTS}/${id}/export`);
/** @param {object} body @param {string} [name] */
export const importLayout = (body, name) =>
  request(`${LAYOUTS}/import${name ? `?name=${encodeURIComponent(name)}` : ''}`, {
    method: 'POST',
    json: body,
  });
export const listFonts = () => request('/api/v1/brands/fonts');

const CANVASES = '/api/v1/canvases';

export const listCanvases = () => request(CANVASES);
/** @param {{ name: string, width: number, height: number }} body */
export const createCanvas = (body) => request(CANVASES, { method: 'POST', json: body });
/** @param {string} id @param {{ name?: string, width?: number, height?: number }} body */
export const updateCanvas = (id, body) =>
  request(`${CANVASES}/${id}`, { method: 'PATCH', json: body });
/** @param {string} id @param {string} name */
export const duplicateCanvas = (id, name) =>
  request(`${CANVASES}/${id}/duplicate`, { method: 'POST', json: { name } });
/** @param {string} id */
export const deleteCanvas = (id) => request(`${CANVASES}/${id}`, { method: 'DELETE' });
/** @param {string} id */
export const exportCanvas = (id) => request(`${CANVASES}/${id}/export`);
/** @param {object} body @param {string} [name] */
export const importCanvas = (body, name) =>
  request(`${CANVASES}/import${name ? `?name=${encodeURIComponent(name)}` : ''}`, {
    method: 'POST',
    json: body,
  });

export const getDoctor = () => request('/api/v1/doctor');

/** Native action registered in Python: returns the app name and version. */
export async function appInfo() {
  const body = await request('/api/bridge/app_info', { method: 'POST', json: {} });
  if (!body?.available) throw new ApiError(body?.reason || 'Not available here', 0);
  return body.result;
}

const GITHUB_SETTINGS = '/api/v1/settings/github';

export const getGithubSettings = () => request(GITHUB_SETTINGS);
/** @param {{ mode: string, local_folder?: string }} body */
export const saveGithubSettings = (body) => request(GITHUB_SETTINGS, { method: 'PUT', json: body });
/** @param {string} source */
export const checkStudioSource = (source) =>
  request('/api/v1/studio/source', { method: 'POST', json: { source } });
/** @param {{ source: string, refresh?: boolean, details?: object }} body */
export const readRepository = (body) =>
  request('/api/v1/studio/repositories', { method: 'POST', json: body });
export const checkGithub = () => request(`${GITHUB_SETTINGS}/check`, { method: 'POST' });

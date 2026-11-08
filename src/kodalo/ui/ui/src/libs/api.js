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

/** Cornea limits on a notification's text. */
const MAX_TITLE = 64;
const MAX_MESSAGE = 256;

/** @param {string} text @param {number} max */
const clip = (text, max) => (text.length > max ? `${text.slice(0, max - 1)}…` : text);

/**
 * Raise a Windows notification through the Cornea bridge. It is only a courtesy, so it never
 * fails: outside the window, or when notifications are off, nothing happens.
 * @param {string} title
 * @param {string} message
 */
export async function notify(title, message) {
  try {
    await request('/api/bridge/show_notification', {
      method: 'POST',
      json: { title: clip(title, MAX_TITLE), message: clip(message, MAX_MESSAGE) },
    });
  } catch {
    // The task's own result is what matters.
  }
}

/**
 * Run a call and notify when it finishes, whether it worked or not. The result or the error is
 * passed on unchanged.
 * @template T
 * @param {string} task what finished, such as "Repository analysis"
 * @param {() => Promise<T>} call
 * @returns {Promise<T>}
 */
async function notifying(task, call) {
  try {
    const result = await call();
    void notify(task, 'Finished.');
    return result;
  } catch (error) {
    void notify(`${task} failed`, error instanceof Error ? error.message : 'Something went wrong.');
    throw error;
  }
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

const PALETTES = '/api/v1/brands/palettes';

export const listPalettes = () => request(PALETTES);
/** @param {{ name: string, colors: object }} body */
export const createPalette = (body) => request(PALETTES, { method: 'POST', json: body });
/** Ask the default AI model for a palette; nothing is saved. */
export const planPaletteSuggestion = () => request(`${PALETTES}/suggest/plan`, { method: 'POST' });
export const suggestPalette = () =>
  notifying('Palette suggestion', () => request(`${PALETTES}/suggest`, { method: 'POST' }));
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

const LAYOUTS = '/api/v1/brands/layouts';

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

const CANVASES = '/api/v1/brands/canvases';

export const listCanvases = () => request(CANVASES);
/** The social platforms a canvas can be made for, with the sizes each recommends. */
export const listSocialPlatforms = () => request('/api/v1/social-platforms');
/** @param {{ name: string, width: number, height: number, platform_id: string }} body */
export const createCanvas = (body) => request(CANVASES, { method: 'POST', json: body });
/** @param {string} id @param {{ name?: string, width?: number, height?: number, platform_id?: string }} body */
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

/**
 * Ask where to save a JSON file with the system's save dialog, then write it there.
 * @param {string} filename suggested name
 * @param {string} text file contents
 * @param {string} [fileType] the save dialog's file type filter
 * @returns {Promise<'saved' | 'cancelled' | 'unavailable'>} `unavailable` outside the window
 */
export async function saveJsonFile(filename, text, fileType = 'JSON files (*.json)') {
  const chosen = await request('/api/bridge/save_file', {
    method: 'POST',
    json: { filename, file_types: [fileType] },
  });
  if (!chosen?.available) return 'unavailable';
  if (!chosen.result) return 'cancelled';
  const written = await request('/api/bridge/write_json_file', {
    method: 'POST',
    json: { path: chosen.result, text },
  });
  if (!written?.available) throw new ApiError(written?.reason || 'The file could not be saved', 0);
  return 'saved';
}

/**
 * Ask which folder to use with the system's folder dialog.
 * @returns {Promise<string>} the folder, or an empty text when the dialog was cancelled
 * @throws {ApiError} outside the window, where there is no dialog
 */
export async function chooseFolder() {
  const chosen = await request('/api/bridge/choose_folder', { method: 'POST', json: {} });
  if (!chosen?.available) {
    throw new ApiError(chosen?.reason || 'Choosing a folder needs the Kodalo window.', 0);
  }
  return typeof chosen.result === 'string' ? chosen.result : '';
}

/**
 * Open a web address in the system's browser. Outside the window, where there is no bridge, the
 * browser opens it in a new tab.
 * @param {string} url
 */
export async function openExternal(url) {
  try {
    const body = await request('/api/bridge/open_external', { method: 'POST', json: { url } });
    if (body?.available) return;
  } catch {
    // Fall through to the browser.
  }
  window.open(url, '_blank', 'noopener');
}

const GITHUB_SETTINGS = '/api/v1/settings/github';

export const getGithubSettings = () => request(GITHUB_SETTINGS);
/** @param {{ mode: string, local_folder?: string, manifest_limit?: number, document_limit?: number, document_max_kb?: number }} body */
export const saveGithubSettings = (body) => request(GITHUB_SETTINGS, { method: 'PUT', json: body });
export const getTheme = () => request('/api/v1/settings/theme');
/** @param {string} platform */
export const getPlatformSettings = (platform) =>
  request(`/api/v1/settings/platforms/${encodeURIComponent(platform)}`);
/**
 * @param {string} platform
 * @param {{ hashtag_count: number, default_hashtags: string[] }} body
 */
export const savePlatformSettings = (platform, body) =>
  request(`/api/v1/settings/platforms/${encodeURIComponent(platform)}`, {
    method: 'PUT',
    json: body,
  });
const INSTAGRAM = '/api/v1/settings/platforms/instagram/connection';
export const getInstagramConnection = () => request(INSTAGRAM);
/**
 * @param {string} accessToken
 * @param {string} accountId
 */
export const connectInstagram = (accessToken, accountId) =>
  request(INSTAGRAM, {
    method: 'PUT',
    json: { access_token: accessToken, account_id: accountId },
  });
export const checkInstagramConnection = () =>
  notifying('Instagram check', () => request(`${INSTAGRAM}/check`, { method: 'POST' }));
export const disconnectInstagram = () => request(INSTAGRAM, { method: 'DELETE' });
const TUNNEL = '/api/v1/settings/platforms/instagram/tunnel';
export const getInstagramTunnel = () => request(TUNNEL);
export const installInstagramTunnel = () => request(TUNNEL, { method: 'POST' });
export const getLogSettings = () => request('/api/v1/settings/logs');
/** @param {{ level?: string, retention_days?: number }} body */
export const saveLogSettings = (body) =>
  request('/api/v1/settings/logs', { method: 'PUT', json: body });
/** @param {string} theme */
export const saveTheme = (theme) =>
  request('/api/v1/settings/theme', { method: 'PUT', json: { theme } });
const REPOSITORIES = '/api/v1/repositories';
export const listRepositories = () => request(REPOSITORIES);
/** @param {string} repoId */
export const getRepository = (repoId) => request(`${REPOSITORIES}/${encodeURIComponent(repoId)}`);
/** @param {string} repoId */
export const removeRepository = (repoId) =>
  request(`${REPOSITORIES}/${encodeURIComponent(repoId)}`, { method: 'DELETE' });
/** @param {string} source */
export const checkRepository = (source) =>
  request(`${REPOSITORIES}/check`, { method: 'POST', json: { source } });
/** @param {{ source: string, refresh?: boolean, details?: object }} body */
export const addRepository = (body) =>
  notifying('Repository added', () => request(REPOSITORIES, { method: 'POST', json: body }));
/** What asking the AI to analyze a repository would send and cost; nothing is sent. */
export const planAnalysis = (/** @type {string} */ repoId) =>
  request(`/api/v1/studio/repositories/${encodeURIComponent(repoId)}/analysis/plan`, {
    method: 'POST',
  });
/** Ask the AI once for parser, framework and tooling configs and save the valid ones. */
export const runAnalysis = (/** @type {string} */ repoId) =>
  notifying('Repository analysis', () =>
    request(`/api/v1/studio/repositories/${encodeURIComponent(repoId)}/analysis`, {
      method: 'POST',
    }),
  );
const readmeUrl = (/** @type {string} */ repoId) =>
  `/api/v1/studio/repositories/${encodeURIComponent(repoId)}/readme`;
/** Read the README and the docs it links to, without AI; a saved result is returned unless refreshed. */
export const readReadme = (/** @type {string} */ repoId, refresh = false) =>
  notifying('README read', () => request(readmeUrl(repoId), { method: 'POST', json: { refresh } }));
/** The saved README analysis. */
export const getReadme = (/** @type {string} */ repoId) => request(readmeUrl(repoId));
/** What asking the AI to read the documents would send and cost; nothing is sent. */
export const planReadmeAnalysis = (/** @type {string} */ repoId) =>
  request(`${readmeUrl(repoId)}/analysis/plan`, { method: 'POST' });
/** Ask the AI once to read the documents and save what it finds with evidence. */
export const runReadmeAnalysis = (/** @type {string} */ repoId) =>
  notifying('Document analysis', () =>
    request(`${readmeUrl(repoId)}/analysis`, { method: 'POST' }),
  );
/**
 * What asking the AI for post ideas would send and cost; nothing is sent.
 * @param {string} repoId
 * @param {{ post_type: string, kind: string, name: string }} body
 */
export const planIdeas = (repoId, body) =>
  request(`/api/v1/studio/repositories/${encodeURIComponent(repoId)}/ideas/plan`, {
    method: 'POST',
    json: body,
  });
/**
 * The post ideas saved for this repository and focus; rejects when none were made yet.
 * @param {string} repoId
 * @param {{ post_type: string, kind: string, name: string }} body
 */
export const getIdeas = (repoId, body) =>
  request(
    `/api/v1/studio/repositories/${encodeURIComponent(repoId)}/ideas?${new URLSearchParams(body)}`,
  );
/**
 * Ask the AI once for a strategy, three angles and five post ideas for a tool or a feature.
 * @param {string} repoId
 * @param {{ post_type: string, kind: string, name: string }} body
 */
export const makeIdeas = (repoId, body) =>
  notifying('Post ideas', () =>
    request(`/api/v1/studio/repositories/${encodeURIComponent(repoId)}/ideas`, {
      method: 'POST',
      json: body,
    }),
  );
/** @typedef {{ brand_id: string, post_type: string, kind: string, name: string, idea_id: string, hook_id: string }} CopyRequest */
const copyUrl = (/** @type {string} */ repoId) =>
  `/api/v1/studio/repositories/${encodeURIComponent(repoId)}/copy`;
/**
 * The post copy saved for this idea and hook; rejects with status 404 when none was written yet.
 * @param {string} repoId
 * @param {CopyRequest} body
 */
export const getCopy = (repoId, body) => request(`${copyUrl(repoId)}?${new URLSearchParams(body)}`);
/**
 * What asking the AI for the post copy would send and cost; nothing is sent.
 * @param {string} repoId
 * @param {CopyRequest} body
 */
export const planCopy = (repoId, body) =>
  request(`${copyUrl(repoId)}/plan`, { method: 'POST', json: body });
/**
 * Ask the AI once to write the slides, caption, alt text and hashtags of a post idea.
 * @param {string} repoId
 * @param {CopyRequest} body
 */
export const makeCopy = (repoId, body) =>
  notifying('Post copy', () => request(copyUrl(repoId), { method: 'POST', json: body }));
/**
 * Save the copy as the user edited it.
 * @param {string} repoId
 * @param {CopyRequest & object} body
 */
export const saveCopy = (repoId, body) => request(copyUrl(repoId), { method: 'PUT', json: body });
const designUrl = (/** @type {string} */ repoId) =>
  `/api/v1/studio/repositories/${encodeURIComponent(repoId)}/design`;
/**
 * The design saved for this post; rejects with status 404 when none was made yet.
 * @param {string} repoId
 * @param {CopyRequest} body
 */
export const getDesign = (repoId, body) =>
  request(`${designUrl(repoId)}?${new URLSearchParams(body)}`);
/**
 * Post the designed post to Instagram. It can take a minute or two.
 * @param {string} repoId
 * @param {Record<string, string>} body the post's request, and `mode` (`light` or `dark`)
 */
export const postToInstagram = (repoId, body) =>
  notifying('Instagram post', () =>
    request(`${designUrl(repoId)}/post`, { method: 'POST', json: body }),
  );
/**
 * Flag a post idea as posted so it is not posted twice, or clear the flag.
 * @param {string} repoId
 * @param {string} ideaId
 * @param {{ post_type: string, kind: string, name: string, posted: boolean }} body
 */
export const setIdeaPosted = (repoId, ideaId, body) =>
  request(`/api/v1/studio/repositories/${repoId}/ideas/${encodeURIComponent(ideaId)}/posted`, {
    method: 'PUT',
    json: body,
  });
/**
 * Make the pictures and caption of the designed post in a new folder inside `body.folder`. It can
 * take a minute.
 * @param {string} repoId
 * @param {Record<string, string>} body the post's request, `mode` and the chosen `folder`
 */
export const exportPost = (repoId, body) =>
  notifying('Post export', () =>
    request(`${designUrl(repoId)}/export`, { method: 'POST', json: body }),
  );
/**
 * What asking the AI to design the post would send and cost; nothing is sent.
 * @param {string} repoId
 * @param {CopyRequest} body
 */
export const planDesign = (repoId, body) =>
  request(`${designUrl(repoId)}/plan`, { method: 'POST', json: body });
/**
 * Ask the AI once how to lay out each slide of the written post.
 * @param {string} repoId
 * @param {CopyRequest} body
 */
export const makeDesign = (repoId, body) =>
  request(designUrl(repoId), { method: 'POST', json: body });
/**
 * Where the drawing of one slide is served.
 * @param {string} repoId
 * @param {CopyRequest} body
 * @param {number} slide
 * @param {string} [version] changes when the design does, so the browser asks again
 */
export const designSvgUrl = (repoId, body, slide, version = '') =>
  `${designUrl(repoId)}/svg?${new URLSearchParams({ ...body, slide: String(slide), v: version })}`;
/**
 * Where an AI-written slide is served as a page, for a sandboxed frame.
 * @param {string} repoId
 * @param {CopyRequest} body
 * @param {number} slide
 * @param {'light' | 'dark'} mode
 * @param {string} [version] changes when the design does, so the browser asks again
 */
export const designSlideUrl = (repoId, body, slide, mode, version = '') =>
  `${designUrl(repoId)}/slide?${new URLSearchParams({ ...body, slide: String(slide), mode, v: version })}`;
export const checkGithub = () =>
  notifying('GitHub check', () => request(`${GITHUB_SETTINGS}/check`, { method: 'POST' }));

const AI = '/api/v1/settings/ai/connections';

export const listAiConnections = () => request(AI);
/** @param {string} provider @param {{ enabled?: boolean, api_key?: string, base_url?: string }} body */
export const saveAiConnection = (provider, body) =>
  request(`${AI}/${provider}`, { method: 'PUT', json: body });
/** @param {string} provider */
export const removeAiConnection = (provider) => request(`${AI}/${provider}`, { method: 'DELETE' });
/** @param {string} provider */
export const setDefaultAiConnection = (provider) =>
  request(`${AI}/default`, { method: 'PUT', json: { provider } });
/** @param {string} provider */
export const testAiConnection = (provider) =>
  notifying('AI connection test', () => request(`${AI}/${provider}/test`, { method: 'POST' }));
/** @param {string} provider */
export const refreshAiModels = (provider) =>
  notifying('AI models refresh', () =>
    request(`${AI}/${provider}/models/refresh`, { method: 'POST' }),
  );
/**
 * @param {string} provider
 * @param {string} name
 * @param {{ max_tokens: number | null, temperature: number | null, timeout_s: number | null }} body
 */
export const saveAiModel = (provider, name, body) =>
  request(`${AI}/${provider}/models/${encodeURIComponent(name)}`, { method: 'PUT', json: body });
/** @param {string} provider @param {string} name */
export const getAiModelDefaults = (provider, name) =>
  request(`${AI}/${provider}/model-defaults?name=${encodeURIComponent(name)}`);
/** @param {string} provider @param {string} name */
export const removeAiModel = (provider, name) =>
  request(`${AI}/${provider}/models/${encodeURIComponent(name)}`, { method: 'DELETE' });
/** @param {string} provider @param {string} name */
export const setDefaultAiModel = (provider, name) =>
  request(`${AI}/${provider}/default-model`, { method: 'PUT', json: { name } });

const AI_SETTINGS = '/api/v1/settings/ai';
export const getAiIdeaCount = () => request(`${AI_SETTINGS}/studio-ideas`);
/** @param {number} count */
export const setAiIdeaCount = (count) =>
  request(`${AI_SETTINGS}/studio-ideas`, { method: 'PUT', json: { idea_count: count } });
export const listAiTaskModels = () => request(`${AI_SETTINGS}/task-models`);
/** @param {string} task @param {string | null} model `null` uses the connection's default model */
export const setAiTaskModel = (task, model) =>
  request(`${AI_SETTINGS}/task-models/${task}`, { method: 'PUT', json: { model } });
/** @param {{ period: string, start?: string, end?: string, limit?: number, offset?: number }} filter */
const aiQuery = ({ period, start, end, limit, offset }) => {
  const query = new URLSearchParams({ period });
  if (period === 'custom' && start) query.set('start', start);
  if (period === 'custom' && end) query.set('end', end);
  if (limit !== undefined) query.set('limit', String(limit));
  if (offset) query.set('offset', String(offset));
  return query.toString();
};
export const getAiHistorySettings = () => request(`${AI_SETTINGS}/history/settings`);
/** @param {{ store_text?: boolean, retention_days?: number }} body */
export const saveAiHistorySettings = (body) =>
  request(`${AI_SETTINGS}/history/settings`, { method: 'PUT', json: body });
/** The calls made to AI providers in a period, newest first, without their text. */
export const listAiHistory = (/** @type {Parameters<typeof aiQuery>[0]} */ filter) =>
  request(`${AI_SETTINGS}/history?${aiQuery(filter)}`);
/** One call with what was sent and what came back, when the text was kept. */
export const getAiCall = (/** @type {string} */ id) =>
  request(`${AI_SETTINGS}/history/${encodeURIComponent(id)}`);
/** Remove every entry of the AI history. */
export const purgeAiHistory = () => request(`${AI_SETTINGS}/history`, { method: 'DELETE' });
/** The tokens used in a period per connection and model and per day. */
export const getAiUsage = (/** @type {Parameters<typeof aiQuery>[0]} */ filter) =>
  request(
    `${AI_SETTINGS}/usage?${aiQuery({ period: filter.period, start: filter.start, end: filter.end })}`,
  );

/** Where the saved icon of a repository is served; the scan time busts the cache. */
export const iconUrl = (/** @type {any} */ repo) =>
  `${REPOSITORIES}/${encodeURIComponent(repo.id)}/icon?v=${encodeURIComponent(repo.last_scanned_at ?? '')}`;

/** Where the saved social preview image of a repository is served; the scan time busts the cache. */
export const socialPreviewUrl = (/** @type {any} */ repo) =>
  `${REPOSITORIES}/${encodeURIComponent(repo.id)}/social-preview?v=${encodeURIComponent(repo.last_scanned_at ?? '')}`;

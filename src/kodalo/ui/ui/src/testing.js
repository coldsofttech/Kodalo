// Helpers for the tests: a fake Python side, sample brands, and a way to "type" into the Fluent
// custom elements (which keep their value as a property and report it with DOM events).
import { fireEvent } from '@testing-library/react';
import { vi } from 'vitest';

const pair = (/** @type {string} */ light, /** @type {string} */ dark) => ({ light, dark });
const font = (/** @type {string} */ family) => ({ family, source: 'bundled' });

/** @param {string} owner */
export const makeRepo = (owner) => ({
  id: 'r1',
  url: `https://github.com/${owner}/repo`,
  owner,
  name: 'repo',
  description: 'A tool',
  homepage: '',
  default_branch: 'main',
  license: 'MIT',
  topics: ['cli'],
  is_private: false,
  is_fork: false,
  is_archived: false,
  last_pushed_at: '2026-10-01T10:00:00Z',
  languages: [{ name: 'Python', bytes: 750, percent: 75 }],
  top_level: [{ path: 'src', type: 'dir' }],
  file_count: 3,
  access_method: 'gh_cli',
  tree_truncated: false,
  warnings: [],
  local_path: '',
  has_social_preview: false,
  has_icon: false,
  icon_path: '',
  icon_checked: false,
  last_scanned_at: '2026-11-02T07:00:00+00:00',
  notable_dirs: [{ path: 'tests', purpose: 'tests' }],
  frameworks: [
    {
      id: 'typer',
      name: 'Typer',
      category: 'cli',
      evidence: 'pyproject.toml: "typer"',
      path: 'pyproject.toml',
    },
  ],
  tooling: [
    {
      id: 'ruff',
      name: 'Ruff',
      category: 'lint_format',
      evidence: 'pyproject.toml: "ruff"',
      path: 'pyproject.toml',
    },
  ],
  manifests: [
    {
      path: 'pyproject.toml',
      ecosystem: 'python',
      is_lockfile: false,
      package_name: 'repo',
      version: '1.0.0',
      dependencies: ['typer', 'rich'],
      dev_dependencies: ['pytest'],
      evidence: 'name = "repo"',
    },
    {
      path: 'uv.lock',
      ecosystem: 'python',
      is_lockfile: true,
      package_name: null,
      version: null,
      dependencies: [],
      dev_dependencies: [],
      evidence: '',
    },
  ],
  is_monorepo: false,
  monorepo_signals: [],
  documentation: {
    readmes: ['README.md'],
    docs_dir: 'docs',
    changelog: 'CHANGELOG.md',
    contributing: '',
    license_file: 'LICENSE',
    code_of_conduct: '',
    security: '',
  },
  skipped: [{ path: '.env', reason: 'secret' }],
});

export const SAMPLE_DATA = () => ({
  schema_version: 1,
  colors: {
    background: pair('#ffffff', '#0b1020'),
    primary: pair('#2563eb', '#60a5fa'),
    secondary: pair('#7c3aed', '#a78bfa'),
    text: pair('#111827', '#f3f4f6'),
    background_alt: pair('#f1f5f9', '#151b30'),
    primary_alt: pair('#1d4ed8', '#93c5fd'),
    secondary_alt: pair('#6d28d9', '#c4b5fd'),
    text_alt: pair('#0f172a', '#e5e7eb'),
  },
  fonts: {
    heading: font('Poppins'),
    heading_alt: font('Space Grotesk'),
    body: font('Inter'),
    body_alt: font('Source Sans 3'),
    mono: font('JetBrains Mono'),
    mono_alt: font('Fira Code'),
  },
  logo: {
    file: null,
    dark_file: null,
    position: 'top_left',
    size_percent: 14,
    padding: 48,
    show_on: 'all',
  },
  layout_id: 'system-default',
});

const canvasRow = (
  /** @type {string} */ id,
  /** @type {string} */ name,
  /** @type {number} */ width,
  /** @type {number} */ height,
  /** @type {'system' | 'user'} */ type = 'system',
  /** @type {string} */ platformId = 'custom',
) => ({
  id,
  name,
  width,
  height,
  type,
  platform_id: platformId,
  platform: platformId === 'instagram' ? 'Instagram' : 'Custom',
  size_concern: /** @type {string | null} */ (null),
  used_by: /** @type {string[]} */ ([]),
  created_at: '2026-11-01T09:00:00+00:00',
  updated_at: '2026-11-01T09:00:00+00:00',
});

export const CANVASES = [
  canvasRow('system-instagram_portrait', 'Instagram portrait', 1080, 1350, 'system', 'instagram'),
  canvasRow('system-instagram_square', 'Instagram square', 1080, 1080, 'system', 'instagram'),
];

export const PLATFORMS = [
  {
    id: 'instagram',
    name: 'Instagram',
    sizes: [
      { name: 'Portrait', width: 1080, height: 1350 },
      { name: 'Square', width: 1080, height: 1080 },
      { name: 'Story', width: 1080, height: 1920 },
    ],
  },
  { id: 'custom', name: 'Custom', sizes: [] },
];

const layoutRow = (
  /** @type {string} */ id,
  /** @type {string} */ name,
  /** @type {'system' | 'user'} */ type = 'system',
  /** @type {Record<string, any>} */ extra = {},
) => ({
  id,
  name,
  type,
  canvas_id: 'system-instagram_portrait',
  margin_top: 96,
  margin_side: 80,
  margin_bottom: 96,
  corner_radius: 24,
  slide_numbers: true,
  footer_text: '',
  align: 'left',
  density: 'regular',
  slides_count: 6,
  used_by: /** @type {string[]} */ ([]),
  created_at: '2026-11-01T09:00:00+00:00',
  updated_at: '2026-11-01T09:00:00+00:00',
  ...extra,
});

export const LAYOUTS = [
  layoutRow('system-default', 'Default'),
  layoutRow('system-compact', 'Compact', 'system', {
    align: 'center',
    density: 'compact',
    slides_count: 4,
  }),
];

export const makeBrand = (
  /** @type {string} */ id,
  /** @type {string} */ name,
  /** @type {boolean} */ isDefault = false,
) => ({
  id,
  name,
  is_default: isDefault,
  data: SAMPLE_DATA(),
  layout: LAYOUTS[0],
  canvas: CANVASES[0],
  created_at: '2026-11-01T09:00:00+00:00',
  updated_at: '2026-11-01T09:00:00+00:00',
});

const paletteRow = (
  /** @type {string} */ id,
  /** @type {string} */ name,
  /** @type {'system' | 'user'} */ type = 'system',
) => ({
  id,
  name,
  type,
  colors: SAMPLE_DATA().colors,
  data: SAMPLE_DATA(),
  created_at: '2026-11-01T09:00:00+00:00',
  updated_at: '2026-11-01T09:00:00+00:00',
});

export const PALETTES = [
  paletteRow('system-midnight', 'Midnight'),
  paletteRow('system-paper', 'Paper'),
];
export const FONTS = [
  { family: 'Inter', category: 'sans', source: 'bundled' },
  { family: 'Poppins', category: 'sans', source: 'bundled' },
  { family: 'Lora', category: 'serif', source: 'bundled' },
  { family: 'Segoe UI', category: 'sans', source: 'system' },
];
export const NO_FAILURES = Array.from({ length: 12 }, () => ({
  color: 'text',
  on: 'background',
  mode: 'light',
  ratio: 12,
  minimum: 4.5,
  passes: true,
}));

/**
 * Fake the Python side. `handler(method, path, body)` returns the JSON to send, `[status, json]`,
 * or undefined for "no such route". Every call is recorded in the returned `calls` list.
 * @param {(method: string, path: string, body: any) => unknown} handler
 */
export function mockApi(handler) {
  /** @type {{ method: string, path: string, body: any }[]} */
  const calls = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (/** @type {string} */ path, /** @type {RequestInit} */ options = {}) => {
      const method = options.method ?? 'GET';
      const body = typeof options.body === 'string' ? JSON.parse(options.body) : options.body;
      calls.push({ method, path, body });
      const result = handler(method, path, body);
      if (result === undefined) {
        return { ok: false, status: 404, json: async () => ({ detail: `${method} ${path}` }) };
      }
      const [status, json] =
        Array.isArray(result) && typeof result[0] === 'number' ? result : [200, result];
      if (status === 204) return { ok: true, status, json: async () => null };
      return { ok: status < 400, status, json: async () => json };
    }),
  );
  return calls;
}

/** Type into a Fluent text or number field, the way its own events report it. */
export function typeInto(/** @type {HTMLElement} */ element, /** @type {string} */ text) {
  Object.assign(element, { value: text });
  fireEvent.input(element);
}

/** Flip a Fluent switch. */
export function setChecked(/** @type {HTMLElement} */ element, /** @type {boolean} */ checked) {
  Object.assign(element, { checked });
  fireEvent.change(element);
}

export const DOCTOR = {
  healthy: true,
  checks: [
    { name: 'Kodalo', ok: true, detail: '0.1.0', required: false },
    { name: 'Python', ok: true, detail: '3.11.9 (requires 3.11+)', required: true },
    { name: 'Fonts', ok: false, detail: 'none installed', required: false },
  ],
};

/**
 * A small in-memory stand-in for the whole API. `state.brands` is what the "database" holds.
 * @param {ReturnType<typeof makeBrand>[]} initial
 */
const AI_PROVIDERS = [
  ['claude_api', 'Claude API', 'api_key', 'https://api.anthropic.com'],
  ['claude_code', 'Claude Code', 'local_cli', ''],
  ['chatgpt_api', 'ChatGPT API', 'api_key', 'https://api.openai.com'],
  ['gemini_api', 'Gemini API', 'api_key', 'https://generativelanguage.googleapis.com'],
];

/** @param {string} provider @param {string} label @param {string} kind @param {string} base */
const makeAiConnection = (provider, label, kind, base) => ({
  provider,
  label,
  kind,
  saved: false,
  enabled: false,
  is_default: false,
  base_url: '',
  default_base_url: base,
  has_key: false,
  key_hint: '',
  status: '',
  status_detail: '',
  checked_at: null,
  default_model: null,
  models: /** @type {any[]} */ ([]),
});

/** @param {string} name @param {string} source */
const makeAiModel = (name, source) => ({
  name,
  source,
  is_default: false,
  max_tokens: null,
  temperature: null,
  timeout_s: null,
});

/** Two sample AI calls: one that kept its text and one that failed. */
export const AI_CALLS = [
  {
    id: 'c1',
    created_at: '2026-11-04T20:15:09+00:00',
    title: 'Suggest a palette',
    purpose: 'palette',
    provider: 'claude_api',
    model: 'claude-haiku-5-5',
    status: 'ok',
    error: '',
    input_tokens: 1200,
    output_tokens: 300,
    has_text: true,
  },
  {
    id: 'c2',
    created_at: '2026-11-03T08:00:00+00:00',
    title: 'Frameworks and tooling for o/repo',
    purpose: 'studio',
    provider: 'claude_code',
    model: 'haiku',
    status: 'failed',
    error: 'Claude Code did not answer.',
    input_tokens: 0,
    output_tokens: 0,
    has_text: false,
  },
];

/** @param {any[]} calls */
function usageOf(calls) {
  /** @type {Map<string, any>} */
  const rows = new Map();
  /** @type {Map<string, any>} */
  const days = new Map();
  for (const call of calls) {
    const key = `${call.provider}/${call.model}`;
    const row = rows.get(key) ?? {
      provider: call.provider,
      model: call.model,
      calls: 0,
      input_tokens: 0,
      output_tokens: 0,
    };
    row.calls += 1;
    row.input_tokens += call.input_tokens;
    row.output_tokens += call.output_tokens;
    rows.set(key, row);
    const day = days.get(call.created_at.slice(0, 10)) ?? {
      day: call.created_at.slice(0, 10),
      input_tokens: 0,
      output_tokens: 0,
    };
    day.input_tokens += call.input_tokens;
    day.output_tokens += call.output_tokens;
    days.set(day.day, day);
  }
  return {
    calls: calls.length,
    input_tokens: calls.reduce((sum, call) => sum + call.input_tokens, 0),
    output_tokens: calls.reduce((sum, call) => sum + call.output_tokens, 0),
    rows: [...rows.values()],
    days: [...days.values()].sort((a, b) => a.day.localeCompare(b.day)),
  };
}

/**
 * The AI history routes, kept in memory. `rest` is the path after /settings/ai/history.
 * @param {{ calls: any[], store_text: boolean, retention_days: number }} history
 * @param {string} method @param {string[]} rest @param {any} body
 */
function aiHistoryRoutes(history, method, rest, body) {
  if (rest[0] === 'settings') {
    if (method === 'PUT') Object.assign(history, body);
    return { store_text: history.store_text, retention_days: history.retention_days };
  }
  if (rest.length === 0 && method === 'DELETE') {
    const deleted = history.calls.length;
    history.calls = [];
    return { deleted };
  }
  if (rest.length === 0) return { total: history.calls.length, items: history.calls };
  const call = history.calls.find((item) => item.id === rest[0]);
  if (!call) return [404, { detail: 'There is no such entry in the history.' }];
  return {
    ...call,
    prompt_text: call.has_text ? 'The prompt that was sent.' : null,
    reply_text: call.has_text ? '{"answer": true}' : null,
  };
}

/**
 * The AI connection routes, kept in memory. `rest` is the path after /settings/ai/connections.
 * @param {any[]} list @param {string} method @param {string[]} rest @param {any} body
 */
function aiRoutes(list, method, rest, body, query = new URLSearchParams()) {
  if (rest.length === 0) return list;
  if (rest[0] === 'default') {
    for (const item of list) item.is_default = item.provider === body.provider;
    return list.find((item) => item.provider === body.provider);
  }
  const item = list.find((candidate) => candidate.provider === rest[0]);
  if (rest.length === 1) {
    if (method === 'DELETE') {
      Object.assign(
        item,
        makeAiConnection(item.provider, item.label, item.kind, item.default_base_url),
      );
      return [204, null];
    }
    item.enabled = body.enabled ?? (item.enabled || !item.saved);
    item.saved = true;
    if (body.api_key) {
      item.has_key = true;
      item.key_hint = body.api_key.slice(-4);
    }
    if (body.base_url !== undefined) item.base_url = body.base_url;
    return item;
  }
  if (rest[1] === 'test') {
    item.status = 'ok';
    item.status_detail = 'Connected. 2 models available.';
    return { provider: item.provider, ok: true, detail: item.status_detail };
  }
  if (rest[1] === 'model-defaults') {
    return { max_tokens: 8192, temperature: 0.7, timeout_s: 90, name: query.get('name') };
  }
  if (rest[1] === 'default-model') {
    for (const model of item.models) model.is_default = model.name === body.name;
    item.default_model = body.name;
    return item.models.find((/** @type {any} */ model) => model.name === body.name);
  }
  if (rest[2] === 'refresh') {
    const manual = item.models.filter((/** @type {any} */ model) => model.source === 'manual');
    item.models = [...manual, makeAiModel('m-a', 'fetched'), makeAiModel('m-b', 'fetched')];
    return item.models;
  }
  const name = decodeURIComponent(rest.slice(2).join('/'));
  if (method === 'DELETE') {
    item.models = item.models.filter((/** @type {any} */ model) => model.name !== name);
    return [204, null];
  }
  let model = item.models.find((/** @type {any} */ candidate) => candidate.name === name);
  if (!model) {
    model = makeAiModel(name, 'manual');
    item.models.push(model);
  }
  Object.assign(model, body);
  return model;
}

export function createBackend(initial = []) {
  const state = {
    brands: initial,
    repos: /** @type {any[]} */ ([makeRepo('o')]),
    canvases: CANVASES.map((canvas) => ({ ...canvas })),
    layouts: LAYOUTS.map((layout) => ({ ...layout })),
    palettes: PALETTES.map((palette) => ({ ...palette })),
    github: {
      mode: 'gh_cli',
      local_folder: '',
      manifest_limit: 10,
      document_limit: 10,
      document_max_kb: 200,
    },
    ai: AI_PROVIDERS.map((provider) => makeAiConnection(...provider)),
    aiHistory: {
      calls: AI_CALLS.map((call) => ({ ...call })),
      store_text: false,
      retention_days: 90,
    },
    repoRead: false,
    contrast: /** @type {any[]} */ (NO_FAILURES),
    doctor: /** @type {any} */ (DOCTOR),
    counter: 0,
    now: 0,
  };
  const find = (/** @type {string} */ id) => state.brands.find((brand) => brand.id === id);
  const touch = (/** @type {any} */ brand) => {
    state.now += 1;
    brand.updated_at = `2026-11-01T10:00:${String(state.now).padStart(2, '0')}+00:00`;
    return brand;
  };
  const withUse = (/** @type {any} */ canvas) => ({
    ...canvas,
    used_by: state.layouts.filter((l) => l.canvas_id === canvas.id).map((l) => l.name),
  });
  const layoutUse = (/** @type {any} */ layout) => ({
    ...layout,
    used_by: state.brands.filter((b) => b.data.layout_id === layout.id).map((b) => b.name),
  });
  const taken = (/** @type {any[]} */ rows, /** @type {string} */ name, id = '') =>
    rows.some((row) => row.id !== id && row.name.toLowerCase() === name.toLowerCase());
  const freeName = (/** @type {any[]} */ rows, /** @type {string} */ name) => {
    let candidate = name;
    for (let n = 2; taken(rows, candidate); n += 1) candidate = `${name} (${n})`;
    return candidate;
  };

  /**
   * One CRUD resource (canvases, palettes or layouts) over a list in `state`.
   * @param {'canvases' | 'palettes' | 'layouts'} key
   * @param {string} format the file format of its exports
   * @param {(id: string, body: any) => any} make builds a new row from a request body
   * @param {(row: any) => any} view the row as the API shows it
   * @param {(row: any, body: any) => void} apply changes a row from an update
   * @param {(row: any) => string[]} users the names of what uses the row
   * @param {(row: any) => any} exported what an export holds besides its format
   */
  const resource =
    (key, format, make, view, apply, users, exported) =>
    /** @type {(method: string, parts: string[], body: any, url: URL) => unknown} */ (
      method,
      parts,
      body,
      url,
    ) => {
      const rows = () => /** @type {any[]} */ (Reflect.get(state, key));
      if (parts.length === 1) {
        if (method === 'GET') return rows().map(view);
        if (taken(rows(), body.name)) {
          return [409, { detail: `A ${key.slice(0, -1)} named "${body.name}" already exists.` }];
        }
        state.counter += 1;
        const created = make(`user-${state.counter}`, body);
        Reflect.set(state, key, [...rows(), created]);
        return [201, view(created)];
      }
      if (parts[1] === 'import') {
        state.counter += 1;
        const name = freeName(rows(), url.searchParams.get('name') ?? body.name);
        const created = make(`user-${state.counter}`, { ...body, name });
        Reflect.set(state, key, [...rows(), created]);
        return [201, view(created)];
      }
      const row = rows().find((r) => r.id === parts[1]);
      if (!row) return [404, { detail: `That ${key.slice(0, -1)} does not exist.` }];
      if (parts[2] === 'export') return { format, version: 1, name: row.name, ...exported(row) };
      if (parts[2] === 'duplicate') {
        state.counter += 1;
        const copy = make(`user-${state.counter}`, { ...row, name: body.name });
        Reflect.set(state, key, [...rows(), copy]);
        return [201, view(copy)];
      }
      if (method === 'GET') return view(row);
      if (row.type === 'system') return [403, { detail: `"${row.name}" is built in.` }];
      if (method === 'DELETE') {
        const names = users(row);
        if (names.length)
          return [409, { detail: `"${row.name}" is used by: ${names.join(', ')}.` }];
        Reflect.set(
          state,
          key,
          rows().filter((r) => r.id !== row.id),
        );
        return [204, null];
      }
      if (body.name !== undefined && taken(rows(), body.name, row.id)) {
        return [409, { detail: `A ${key.slice(0, -1)} named "${body.name}" already exists.` }];
      }
      apply(row, body);
      return view(row);
    };

  const canvasRoutes = resource(
    'canvases',
    'kodalo-canvas',
    (id, body) =>
      canvasRow(id, body.name, body.width, body.height, 'user', body.platform_id ?? 'custom'),
    withUse,
    (row, body) => Object.assign(row, body),
    (row) => withUse(row).used_by,
    (row) => ({ width: row.width, height: row.height }),
  );
  const layoutRoutes = resource(
    'layouts',
    'kodalo-layout',
    (id, body) => layoutRow(id, body.name, 'user', { ...(body.settings ?? body) }),
    layoutUse,
    (row, body) => Object.assign(row, body),
    (row) => layoutUse(row).used_by,
    (row) => ({ ...row, canvas: { name: 'Instagram portrait', width: 1080, height: 1350 } }),
  );
  const paletteRoutes = resource(
    'palettes',
    'kodalo-palette',
    (id, body) => ({
      ...paletteRow(id, body.name, 'user'),
      colors: body.colors ?? SAMPLE_DATA().colors,
    }),
    (row) => ({ ...row, data: { ...row.data, colors: row.colors } }),
    (row, body) => Object.assign(row, body),
    () => [],
    (row) => ({ colors: row.colors }),
  );
  /** @type {(method: string, path: string, body: any) => unknown} */
  const handler = (method, path, body) => {
    const url = new URL(path, 'http://app');
    const parts = url.pathname.replace('/api/v1/', '').split('/');
    if (url.pathname === '/api/bridge/app_info') {
      return { available: true, result: { name: 'Kodalo', version: '1.2.3' } };
    }
    if (parts[0] === 'repositories' && parts[1] === 'check') {
      if (state.github.mode === 'local_folder') {
        const suggested = { owner: '', repo: 'proj', default_branch: 'main' };
        return {
          kind: 'local_folder',
          value: body.source,
          name: 'proj',
          stored_id: state.repoRead ? 'r1' : null,
          suggested,
        };
      }
      if (!body.source.startsWith('https://')) return [422, { detail: 'Use a GitHub address.' }];
      return { kind: 'github', value: body.source, name: 'repo', stored_id: null, suggested: null };
    }
    if (parts[0] === 'repositories' && parts[1] && method === 'GET') return state.repos[0];
    if (parts[0] === 'repositories' && parts[1] && method === 'DELETE') {
      state.repos = [];
      return null;
    }
    if (parts[0] === 'repositories' && method === 'GET') return state.repos;
    if (parts[0] === 'repositories') {
      const local = state.github.mode === 'local_folder';
      if (local && !state.repoRead && !body.details)
        return [422, { detail: 'Please fill in: owner.' }];
      state.repoRead = true;
      state.repos = [makeRepo(body.details?.owner ?? 'o')];
      return state.repos[0];
    }
    if (parts[0] === 'settings') {
      if (parts[1] === 'platforms' && parts[2] === 'instagram' && parts[3] === 'connection') {
        const none = {
          connected: false,
          username: '',
          account_id: '',
          account_type: '',
          token_hint: '',
          connected_at: '',
        };
        if (method === 'PUT') {
          if (body.access_token === 'bad')
            return [502, { detail: 'Instagram rejected the token.' }];
          state.instagram = {
            connected: true,
            username: 'sweepito',
            account_id: body.account_id,
            account_type: '',
            token_hint: body.access_token.slice(-4),
            connected_at: '2026-11-07T10:00:00+00:00',
          };
        }
        if (method === 'DELETE') state.instagram = none;
        return state.instagram ?? none;
      }
      if (parts[1] === 'platforms') {
        state.platforms ??= {};
        const current = state.platforms[parts[2]] ?? {
          hashtag_count: 5,
          default_hashtags: [],
          use_social_preview: false,
          use_repo_icon: false,
          use_icons: false,
          build_custom_images: false,
          use_ai_templates: false,
        };
        if (method === 'PUT') state.platforms[parts[2]] = { ...body };
        return { platform: parts[2], ...(state.platforms[parts[2]] ?? current) };
      }
      if (parts[1] === 'theme') {
        if (method === 'PUT') state.theme = body.theme;
        return { theme: state.theme ?? 'system' };
      }
      if (parts[1] === 'logs') {
        if (method === 'PUT') state.logs = { ...(state.logs ?? {}), ...body };
        return {
          level: 'INFO',
          retention_days: 90,
          folder: 'C:/Kodalo/logs',
          ...(state.logs ?? {}),
        };
      }
      if (parts[1] === 'ai' && parts[2] === 'history') {
        return aiHistoryRoutes(state.aiHistory, method, parts.slice(3), body);
      }
      if (parts[1] === 'ai' && parts[2] === 'usage') return usageOf(state.aiHistory.calls);
      if (parts[1] === 'ai' && parts[2] === 'connections')
        return aiRoutes(state.ai, method, parts.slice(3), body, url.searchParams);
      if (parts[2] === 'check') return { mode: state.github.mode, ok: true, detail: 'Works.' };
      if (method === 'PUT') state.github = { local_folder: '', ...state.github, ...body };
      return state.github;
    }
    if (parts[0] === 'palettes') return paletteRoutes(method, parts, body, url);
    if (parts[0] === 'layouts') return layoutRoutes(method, parts, body, url);
    if (parts[0] === 'canvases') return canvasRoutes(method, parts, body, url);
    if (parts[0] === 'social-platforms') return PLATFORMS;
    if (parts[0] === 'brands' && parts[1] === 'fonts') return FONTS;
    if (parts[0] === 'doctor') return state.doctor;
    if (parts[0] !== 'brands') return undefined;
    if (parts.length === 1) {
      if (method === 'GET') return state.brands;
      state.counter += 1;
      const brand = makeBrand(`new-${state.counter}`, body.name, state.brands.length === 0);
      if (state.brands.some((item) => item.name.toLowerCase() === body.name.toLowerCase())) {
        return [409, { detail: `A brand named "${body.name}" already exists.` }];
      }
      state.brands = [...state.brands, brand];
      return [201, brand];
    }
    if (parts[1] === 'contrast') return state.contrast;
    if (parts[1] === 'import') {
      state.counter += 1;
      const brand = makeBrand(`new-${state.counter}`, url.searchParams.get('name') ?? body.name);
      state.brands = [...state.brands, brand];
      return [201, brand];
    }
    const brand = find(parts[1]);
    if (!brand) return [404, { detail: 'That brand does not exist.' }];
    const action = parts[2];
    if (action === undefined) {
      if (method === 'DELETE') {
        state.brands = state.brands.filter((item) => item.id !== brand.id);
        if (brand.is_default && state.brands[0]) state.brands[0].is_default = true;
        return [204, null];
      }
      if (
        body.name !== undefined &&
        state.brands.some((b) => b.id !== brand.id && b.name === body.name)
      ) {
        return [409, { detail: `A brand named "${body.name}" already exists.` }];
      }
      Object.assign(brand, body);
      brand.layout = state.layouts.find((l) => l.id === brand.data.layout_id) ?? brand.layout;
      brand.canvas = state.canvases.find((c) => c.id === brand.layout.canvas_id) ?? brand.canvas;
      return touch(brand);
    }
    if (action === 'default') {
      for (const item of state.brands) item.is_default = item.id === brand.id;
      return touch(brand);
    }
    if (action === 'duplicate') {
      state.counter += 1;
      const copy = makeBrand(`new-${state.counter}`, body.name);
      state.brands = [...state.brands, copy];
      return [201, copy];
    }
    if (action === 'export') {
      return { format: 'kodalo-brand', version: 1, name: brand.name, data: brand.data, logos: {} };
    }
    if (action === 'logo') {
      const dark = url.searchParams.get('variant') === 'dark';
      const key = dark ? 'dark_file' : 'file';
      Reflect.set(brand.data.logo, key, method === 'PUT' ? `${'a'.repeat(32)}.png` : null);
      return touch(brand);
    }
    return undefined;
  };
  return { state, handler };
}

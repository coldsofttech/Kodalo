import { afterEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import InstagramPost from './Post.jsx';
import { mockApi } from '../../../../testing.js';

afterEach(() => vi.unstubAllGlobals());

const request = { brand_id: 'b1', post_type: 'tool', kind: '', name: '', idea_id: 'idea-1' };
const repo = { id: 'o~r' };
const account = {
  connected: true,
  username: 'sweepito',
  account_id: '1',
  account_type: '',
  token_hint: '1234',
  connected_at: '',
};
const none = { ...account, connected: false, username: '' };
const exportResult = {
  folder: 'C:\\Posts\\what-if',
  pictures: ['C:\\Posts\\what-if\\slide-1.jpg', 'C:\\Posts\\what-if\\slide-2.jpg'],
  caption_file: 'C:\\Posts\\what-if\\caption.txt',
};

/**
 * @param {any} connection
 * @param {{ onPost?: (body: any) => unknown, tunnel?: { installed: boolean }, folder?: unknown,
 *   onExport?: (body: any) => unknown }} [options]
 */
function backend(connection, options = {}) {
  const {
    onPost = () => ({ media_id: '9', permalink: 'https://x.test/p/9' }),
    tunnel = { installed: true },
    folder = 'C:\\Posts',
    onExport = () => exportResult,
  } = options;
  return mockApi((method, path, body) => {
    if (path.endsWith('/instagram/connection')) return connection;
    if (path.endsWith('/instagram/tunnel')) {
      if (method === 'POST') tunnel.installed = true;
      return tunnel;
    }
    if (path.endsWith('/api/bridge/choose_folder')) return { available: true, result: folder };
    if (method === 'POST' && path.endsWith('/design/post')) return onPost(body);
    if (method === 'POST' && path.endsWith('/design/export')) return onExport(body);
    return [404, { detail: 'No such route.' }];
  });
}

function show(slides = 3) {
  return render(<InstagramPost repo={repo} request={request} mode="dark" slides={slides} />);
}

/** Open the banner and confirm, as the person does. */
async function postIt() {
  await userEvent.click(await screen.findByLabelText('Post to Instagram'));
  await userEvent.click(screen.getByLabelText('Confirm post'));
}

describe('InstagramPost', () => {
  it('shows only the buttons, then the details banner, then posts in the shown mode', async () => {
    const calls = backend(account);
    const { container } = show();

    const postButton = await screen.findByLabelText('Post to Instagram');
    expect(screen.getByLabelText('Export slides and caption')).toBeInTheDocument();
    expect(screen.queryByRole('region', { name: 'Instagram post' })).not.toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();

    await userEvent.click(postButton);
    const banner = screen.getByRole('region', { name: 'Instagram post' });
    expect(banner).toHaveTextContent('a carousel of 3 slides');
    expect(banner).toHaveTextContent('sweepito');
    expect(banner).toHaveTextContent('Cloudflared');
    expect(screen.getByRole('alert')).toHaveTextContent('publishes the post');
    expect(calls.some((call) => call.path.endsWith('/design/post'))).toBe(false);
    await userEvent.click(screen.getByLabelText('Confirm post'));

    expect(await screen.findByText(/Posted\./)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'View the post' })).toBeInTheDocument();
    expect(calls.find((call) => call.path.endsWith('/design/post')).body).toEqual({
      ...request,
      mode: 'dark',
    });
  });

  it('hides Post until Instagram is connected but still offers Export', async () => {
    backend(none);
    show();

    expect(await screen.findByLabelText('Export slides and caption')).toBeEnabled();
    expect(screen.queryByLabelText('Post to Instagram')).not.toBeInTheDocument();
  });

  it('can be cancelled at the banner', async () => {
    const calls = backend(account);
    show(1);

    await userEvent.click(await screen.findByLabelText('Post to Instagram'));
    expect(screen.getByRole('region', { name: 'Instagram post' })).toHaveTextContent(
      'a single image',
    );
    await userEvent.click(screen.getByLabelText('Cancel'));

    expect(screen.queryByRole('region', { name: 'Instagram post' })).not.toBeInTheDocument();
    expect(calls.some((call) => call.path.endsWith('/design/post'))).toBe(false);
  });

  it('does not install cloudflared when it is already there', async () => {
    const calls = backend(account);
    show();

    await postIt();

    expect(await screen.findByText(/Posted\./)).toBeInTheDocument();
    expect(calls.some((call) => call.method === 'POST' && call.path.endsWith('/tunnel'))).toBe(
      false,
    );
  });

  it('installs cloudflared first, with its own screen, when it is missing', async () => {
    const calls = backend(account, { tunnel: { installed: false } });
    const fetchMock = globalThis.fetch;
    /** @type {() => void} */
    let release = () => {};
    const gate = new Promise((resolve) => {
      release = () => resolve(undefined);
    });
    vi.stubGlobal(
      'fetch',
      vi.fn(async (/** @type {string} */ path, /** @type {RequestInit | undefined} */ options) => {
        if (options?.method === 'POST' && path.endsWith('/tunnel')) await gate;
        return fetchMock(path, options);
      }),
    );
    show();

    await postIt();

    expect(await screen.findByText(/Installing Cloudflared/)).toBeInTheDocument();
    expect(calls.some((call) => call.path.endsWith('/design/post'))).toBe(false);
    release();

    expect(await screen.findByText(/Posted\./)).toBeInTheDocument();
    const order = calls.filter((call) => call.method === 'POST').map((call) => call.path);
    expect(order.filter((path) => !path.includes('/bridge/'))[0]).toMatch(/\/instagram\/tunnel$/);
    expect(order.at(-1)).toMatch(/\/design\/post$/);
    expect(screen.queryByText(/Installing Cloudflared/)).toBeNull();
  });

  it('shows why cloudflared could not be installed and does not post', async () => {
    const calls = backend(account, { tunnel: { installed: false } });
    const fetchMock = globalThis.fetch;
    vi.stubGlobal(
      'fetch',
      vi.fn(async (/** @type {string} */ path, /** @type {RequestInit | undefined} */ options) =>
        options?.method === 'POST' && path.endsWith('/tunnel')
          ? {
              ok: false,
              status: 502,
              json: async () => ({ detail: 'Could not download cloudflared.' }),
            }
          : fetchMock(path, options),
      ),
    );
    show();

    await postIt();

    expect(await screen.findByText('Could not download cloudflared.')).toBeInTheDocument();
    expect(calls.some((call) => call.path.endsWith('/design/post'))).toBe(false);
  });

  it('shows why a post failed', async () => {
    backend(account, {
      onPost: () => [502, { detail: 'Instagram refused the post: bad image.' }],
    });
    show();

    await postIt();

    expect(await screen.findByText('Instagram refused the post: bad image.')).toBeInTheDocument();
  });

  it('exports into the folder chosen in the window dialog, in the shown mode', async () => {
    const calls = backend(none);
    show();

    await userEvent.click(await screen.findByLabelText('Export slides and caption'));

    expect(await screen.findByText(/Exported 2 pictures and caption\.txt/)).toBeInTheDocument();
    expect(screen.getByText(/C:\\Posts\\what-if/)).toBeInTheDocument();
    expect(calls.find((call) => call.path.endsWith('/design/export')).body).toEqual({
      ...request,
      mode: 'dark',
      folder: 'C:\\Posts',
    });
    expect(calls.some((call) => call.path.endsWith('/design/post'))).toBe(false);
  });

  it('exports nothing when the folder dialog is cancelled', async () => {
    const calls = backend(none, { folder: null });
    show();

    await userEvent.click(await screen.findByLabelText('Export slides and caption'));

    expect(await screen.findByLabelText('Export slides and caption')).toBeEnabled();
    expect(calls.some((call) => call.path.endsWith('/design/export'))).toBe(false);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('shows why an export failed', async () => {
    backend(none, {
      onExport: () => [422, { detail: 'Kodalo could not write to that folder.' }],
    });
    show();

    await userEvent.click(await screen.findByLabelText('Export slides and caption'));

    expect(await screen.findByText('Kodalo could not write to that folder.')).toBeInTheDocument();
  });
});

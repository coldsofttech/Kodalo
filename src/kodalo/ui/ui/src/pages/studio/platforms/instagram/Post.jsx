import { useEffect, useState } from 'react';
import {
  chooseFolder,
  exportPost,
  getInstagramConnection,
  getInstagramTunnel,
  installInstagramTunnel,
  openExternal,
  postToInstagram,
} from '../../../../libs/api.js';
import AiOverlay from '../../../../components/AiOverlay.jsx';
import { Button } from '../../../../components/controls.jsx';

/**
 * The heading of the slides with the Post and Export icon buttons at its right. Post is only there
 * once Instagram is connected: it opens a banner with the details and asks once more, then posts.
 * The server makes the pictures and shares them through a temporary public address while Instagram
 * fetches them, which can take a minute or two. Export writes the pictures and a caption file into
 * a folder to post by hand.
 * @param {{ title: import('react').ReactNode, repo: any, request: any, mode: 'light' | 'dark', slides: number }} props
 */
export default function InstagramPost({ title, repo, request, mode, slides }) {
  const [account, setAccount] = useState(/** @type {any} */ (null));
  const [confirming, setConfirming] = useState(false);
  const [stage, setStage] = useState(
    /** @type {'' | 'installing' | 'posting' | 'exporting'} */ (''),
  );
  const [posted, setPosted] = useState(/** @type {{ permalink: string } | null} */ (null));
  const [exported, setExported] = useState(
    /** @type {{ folder: string, count: number } | null} */ (null),
  );
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    getInstagramConnection().then(
      (found) => alive && setAccount(found),
      (failure) => alive && setError(failure.message),
    );
    return () => {
      alive = false;
    };
  }, []);

  function start() {
    setError('');
    setPosted(null);
    setExported(null);
  }

  async function post() {
    setConfirming(false);
    start();
    setStage('posting');
    try {
      const tunnel = await getInstagramTunnel();
      if (!tunnel.installed) {
        setStage('installing');
        await installInstagramTunnel();
        setStage('posting');
      }
      setPosted(await postToInstagram(repo.id, { ...request, mode }));
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Something went wrong.');
    } finally {
      setStage('');
    }
  }

  async function exportSlides() {
    setConfirming(false);
    start();
    try {
      const folder = await chooseFolder();
      if (!folder) return;
      setStage('exporting');
      const done = await exportPost(repo.id, { ...request, mode, folder });
      setExported({ folder: done.folder, count: done.pictures.length });
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Something went wrong.');
    } finally {
      setStage('');
    }
  }

  const busy = stage !== '';
  const connected = Boolean(account?.connected);
  const what = slides === 1 ? 'a single image' : `a carousel of ${slides} slides`;
  return (
    <>
      {stage === 'installing' ? (
        <AiOverlay
          message="Installing Cloudflared, a third-party tool required for posting directly to Instagram. This can take a minute."
          icon="bi-download"
        />
      ) : null}
      {stage === 'posting' ? (
        <AiOverlay
          message="Posting to Instagram. This can take a minute or two."
          icon="bi-instagram"
        />
      ) : null}
      {stage === 'exporting' ? (
        <AiOverlay message="Exporting the slides and the caption." icon="bi-arrow-repeat" />
      ) : null}
      <div className="post-title-row">
        {title}
        <div className="row actions">
          {connected ? (
            <Button
              appearance="accent"
              label="Post to Instagram"
              title="Post to Instagram"
              disabled={busy}
              onClick={() => setConfirming(true)}
            >
              <i className="bi bi-send" aria-hidden="true" />
            </Button>
          ) : null}
          <Button
            label="Export slides and caption"
            title="Export the slides as pictures and the caption as a text file"
            disabled={busy}
            onClick={exportSlides}
          >
            <i className="bi bi-download" aria-hidden="true" />
          </Button>
        </div>
      </div>
      {confirming && connected ? (
        <section className="design-post" aria-label="Instagram post">
          <p>
            Posts {what} to <strong>{account.username}</strong> on Instagram, with the caption and
            hashtags below and the {mode} colors shown.
          </p>
          <p className="hint">
            Kodalo will install Cloudflared, a third-party tool that is required for posting
            directly to Instagram.
          </p>
          <p role="alert" className="alert">
            This publishes the post on Instagram now. Post it?
          </p>
          <div className="row actions">
            <Button appearance="accent" label="Confirm post" title="Confirm post" onClick={post}>
              <i className="bi bi-check-lg" aria-hidden="true" />
            </Button>
            <Button label="Cancel" title="Cancel" onClick={() => setConfirming(false)}>
              <i className="bi bi-x-lg" aria-hidden="true" />
            </Button>
          </div>
        </section>
      ) : null}
      {posted ? (
        <p role="status" className="notice">
          Posted.{' '}
          {posted.permalink ? (
            <a
              href={posted.permalink}
              onClick={(event) => {
                event.preventDefault();
                openExternal(posted.permalink);
              }}
            >
              View the post
            </a>
          ) : null}
        </p>
      ) : null}
      {exported ? (
        <p role="status" className="notice">
          Exported {exported.count === 1 ? 'the picture' : `${exported.count} pictures`} and
          caption.txt to {exported.folder}.
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="alert">
          {error}
        </p>
      ) : null}
    </>
  );
}

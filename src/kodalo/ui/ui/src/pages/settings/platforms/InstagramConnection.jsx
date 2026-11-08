import { useEffect, useState } from 'react';
import {
  checkInstagramConnection,
  connectInstagram,
  disconnectInstagram,
  getInstagramConnection,
  openExternal,
} from '../../../libs/api.js';
import { Button, TextField } from '../../../components/controls.jsx';
import { useUnsavedGuard } from '../../../libs/unsaved.js';

/** @typedef {{ connected: boolean, username: string, account_id: string, account_type: string, token_hint: string, connected_at: string }} InstagramAccount */

const GUIDE_URL = 'https://developers.facebook.com/docs/instagram-platform';

/** Connects Kodalo to Instagram with an access token and account ID. The token is kept in the
 * system keychain. */
export default function InstagramConnection() {
  const [account, setAccount] = useState(/** @type {InstagramAccount | null} */ (null));
  const [token, setToken] = useState('');
  const [accountId, setAccountId] = useState('');
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useUnsavedGuard(Boolean(token || accountId));

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

  /**
   * @param {() => Promise<InstagramAccount>} action
   * @param {string} done
   */
  async function run(action, done) {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      setAccount(await action());
      setToken('');
      setAccountId('');
      setNotice(done);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Something went wrong.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="instagram-connection">
      <h3>Instagram connection</h3>
      {account?.connected ? (
        <p>
          Connected as <strong>{account.username}</strong>
          {account.account_type ? ` (${account.account_type.toLowerCase()})` : ''}. The token ending
          in {account.token_hint} is kept in your system keychain.
        </p>
      ) : (
        <p className="hint">
          Not connected. Create a token for your Business or Creator account in the Meta developer
          dashboard and paste it here with the account's ID. Kodalo never asks for your Instagram
          password.
        </p>
      )}
      <details className="guide">
        <summary>How to get an access token</summary>
        <ol>
          <li>
            In Instagram, open Settings &gt; Account type and switch to a professional account, then
            choose Creator and pick a category.
          </li>
          <li>
            Sign in to developers.facebook.com with a Facebook account, go to My apps &gt; Create
            app, enter an app name and choose "Manage messaging &amp; content on Instagram".
          </li>
          <li>
            In the app dashboard, open Instagram app &gt; Use cases &gt; Customize, then use Unified
            login to create a business portfolio. Verifying it is optional for independent
            developers.
          </li>
          <li>
            Configure your app and create a new configuration. Make sure Instagram accounts is
            selected as an asset, the system-user access token is set to never expire, and the
            instagram_basic and instagram_content_publish permissions are added, then select Create.
          </li>
          <li>
            In the next step, Generate access tokens, select Add account, then add your account as
            an Instagram tester and accept the invitation on Instagram.
          </li>
          <li>Select Generate token, sign in, and copy the token.</li>
          <li>Paste the app ID and the token below and select Connect.</li>
        </ol>
        <p>
          <a
            href={GUIDE_URL}
            onClick={(event) => {
              event.preventDefault();
              openExternal(GUIDE_URL);
            }}
          >
            Open Instagram's guide
          </a>
        </p>
      </details>
      <p className="hint">
        Kodalo will install <strong>Cloudflared</strong>, a third-party tool that is required for
        posting directly to Instagram.
      </p>
      <TextField
        label="Instagram account ID"
        value={accountId}
        maxLength={40}
        onChange={setAccountId}
      />
      <TextField
        label="Access token"
        type="password"
        value={token}
        maxLength={1024}
        hint={account?.connected ? 'Enter a new token to replace the saved one.' : ''}
        onChange={setToken}
      />
      <div className="row actions">
        <Button
          appearance="accent"
          label={account?.connected ? 'Replace token' : 'Connect'}
          title={account?.connected ? 'Replace token' : 'Connect'}
          disabled={busy || !token.trim() || !accountId.trim()}
          onClick={() => run(() => connectInstagram(token.trim(), accountId.trim()), 'Connected.')}
        >
          <i className="bi bi-plug" aria-hidden="true" />
        </Button>
        {account?.connected ? (
          <>
            <Button
              label="Check connection"
              title="Check connection"
              disabled={busy}
              onClick={() => run(checkInstagramConnection, 'The token works.')}
            >
              <i className="bi bi-arrow-repeat" aria-hidden="true" />
            </Button>
            <Button
              label="Disconnect"
              title="Disconnect"
              disabled={busy}
              onClick={() => run(disconnectInstagram, 'Disconnected.')}
            >
              <i className="bi bi-x-circle" aria-hidden="true" />
            </Button>
          </>
        ) : null}
      </div>
      {error ? (
        <p role="alert" className="alert">
          {error}
        </p>
      ) : null}
      {notice ? (
        <p role="status" className="notice">
          {notice}
        </p>
      ) : null}
    </div>
  );
}

import { useEffect, useState } from 'react';
import { appInfo, getDoctor } from '../libs/api.js';
import { Button } from '../components/controls.jsx';

/** @param {{ ok: boolean, required: boolean }} check */
function status({ ok, required }) {
  if (ok) return 'OK';
  return required ? 'Failed' : 'Warning';
}

export default function AboutPage() {
  const [info, setInfo] = useState(/** @type {{ name: string, version: string } | null} */ (null));
  const [report, setReport] = useState(/** @type {any} */ (null));
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    appInfo().then(
      (result) => alive && setInfo(result),
      () => undefined, // The version is a nicety; the page works without it.
    );
    return () => {
      alive = false;
    };
  }, []);

  async function check() {
    setBusy(true);
    setError('');
    try {
      setReport(await getDoctor());
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'The check could not be run.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="about card" aria-labelledby="about-title">
      <img className="about-logo logo-light" src="/logo-light.svg" alt="" />
      <img className="about-logo logo-dark" src="/logo-dark.svg" alt="" />
      <h1 id="about-title">About Kodalo</h1>
      {info ? <p className="hint">Version {info.version}</p> : null}
      <p>
        Kodalo turns your GitHub repositories into accurate, on-brand Instagram posts. It runs on
        this computer, keeps your brands and content here, and lets you choose your own AI provider.
        Nothing is posted without your approval.
      </p>
      <p>
        If something does not look right, check the installation. It reads your setup and your local
        data, and changes nothing.
      </p>
      <h2>Third-party software</h2>
      <p>
        Kodalo will install <strong>Cloudflared</strong>, a third-party tool that is required for
        posting directly to Instagram.
      </p>
      <Button appearance="accent" disabled={busy} onClick={check}>
        Check installation
      </Button>
      {error ? (
        <p role="alert" className="alert">
          {error}
        </p>
      ) : null}
      {report ? (
        <>
          <p role="status" className={report.healthy ? 'notice' : 'alert'}>
            {report.healthy ? 'Everything looks good.' : 'One or more required checks failed.'}
          </p>
          <table className="checks">
            <caption className="visually-hidden">Installation checks</caption>
            <thead>
              <tr>
                <th scope="col">Check</th>
                <th scope="col">Result</th>
                <th scope="col">Detail</th>
              </tr>
            </thead>
            <tbody>
              {report.checks.map((/** @type {any} */ check_) => (
                <tr key={check_.name}>
                  <th scope="row">{check_.name}</th>
                  <td>{status(check_)}</td>
                  <td>{check_.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : null}
    </section>
  );
}

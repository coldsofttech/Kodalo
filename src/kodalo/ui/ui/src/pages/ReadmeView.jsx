import { useState } from 'react';
import { getReadme, planReadmeAnalysis, runReadmeAnalysis } from '../api.js';
import { Button } from '../components/controls.jsx';

/** @param {string} value */
const orDash = (value) => value || '-';

/**
 * The Analyze step: what the README and the docs say. They are read without AI first; "Refresh with
 * AI" sends their text to the AI once, after the user has seen what would be sent, and keeps what
 * it finds with a quote.
 *
 * @param {{ repo: any, readme: any, busy: boolean, onRun: (action: () => Promise<void>) => void,
 *   onChange: (readme: any) => void, onRefresh: () => void, onNext: () => void, onBack: () => void }} props
 */
export default function ReadmeView({
  repo,
  readme,
  busy,
  onRun,
  onChange,
  onRefresh,
  onNext,
  onBack,
}) {
  const [plan, setPlan] = useState(/** @type {any} */ (null));
  const [message, setMessage] = useState('');

  const ask = () =>
    onRun(async () => {
      setMessage('');
      const next = await planReadmeAnalysis(repo.id);
      if (next.documents.length === 0) {
        setMessage('No document was read, so there is nothing to send.');
        return;
      }
      setPlan(next);
    });

  const proceed = () =>
    onRun(async () => {
      setPlan(null);
      const result = await runReadmeAnalysis(repo.id);
      setMessage(
        [
          `Saved ${result.installation} installation method(s), ${result.capabilities} capabilities, ${result.features} feature(s) and ${result.use_cases} use case(s).`,
          ...result.skipped,
        ].join(' '),
      );
      onChange(await getReadme(repo.id));
    });

  return (
    <>
      <h2>What {repo.name} is</h2>
      <h3>Purpose</h3>
      {readme.summary ? (
        <>
          <p>{readme.tagline}</p>
          <p className="hint">{readme.summary}</p>
        </>
      ) : (
        <p className="hint">No introduction was found in the documents.</p>
      )}

      <h3>Installation</h3>
      {readme.installation.length === 0 ? (
        <p className="hint">No way to install it was found in the documents.</p>
      ) : (
        <table className="checks">
          <caption className="visually-hidden">Installation</caption>
          <thead>
            <tr>
              <th scope="col">Method</th>
              <th scope="col">Command</th>
              <th scope="col">Found in</th>
            </tr>
          </thead>
          <tbody>
            {readme.installation.map((/** @type {any} */ item, /** @type {number} */ index) => (
              <tr key={`${item.method}-${index}`}>
                <th scope="row">{item.method}</th>
                <td>{orDash(item.command)}</td>
                <td>{item.evidence.file}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h3>Capabilities</h3>
      {readme.capabilities.length === 0 ? (
        <p className="hint">No features or commands were listed in the documents.</p>
      ) : (
        <table className="checks">
          <caption className="visually-hidden">Capabilities</caption>
          <thead>
            <tr>
              <th scope="col">Capability</th>
              <th scope="col">Description</th>
              <th scope="col">Found in</th>
            </tr>
          </thead>
          <tbody>
            {readme.capabilities.map((/** @type {any} */ item, /** @type {number} */ index) => (
              <tr key={`${item.name}-${index}`}>
                <th scope="row">
                  {item.name}
                  {item.note ? <span className="topic">{item.note}</span> : null}
                </th>
                <td>{orDash(item.description)}</td>
                <td>{item.evidence.file}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h3>Features</h3>
      {readme.features.length === 0 ? (
        <p className="hint">
          Features group the capabilities, so the AI writes them. Press Refresh with AI to ask;
          nothing is sent until you agree.
        </p>
      ) : (
        <ul>
          {readme.features.map((/** @type {any} */ item, /** @type {number} */ index) => (
            <li key={`${item.name}-${index}`}>
              <strong>{item.name}</strong> {item.description}
            </li>
          ))}
        </ul>
      )}

      <h3>Use cases</h3>
      {readme.use_cases.length === 0 ? (
        <p className="hint">
          Use cases need judgement, so the AI writes them. Press Refresh with AI to ask; nothing is
          sent until you agree.
        </p>
      ) : (
        <ul>
          {readme.use_cases.map((/** @type {any} */ item, /** @type {number} */ index) => (
            <li key={`${item.title}-${index}`}>
              <strong>{item.title}</strong> {item.description}
            </li>
          ))}
        </ul>
      )}

      <h3>Documents</h3>
      <table className="checks">
        <caption className="visually-hidden">Documents</caption>
        <thead>
          <tr>
            <th scope="col">Document</th>
            <th scope="col">Status</th>
            <th scope="col">Reason</th>
          </tr>
        </thead>
        <tbody>
          {readme.documents.map((/** @type {any} */ item) => (
            <tr key={item.path}>
              <th scope="row">{item.path}</th>
              <td>
                <span className="topic">{item.status}</span>
              </td>
              <td>{orDash(item.reason)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {readme.warnings.map((/** @type {string} */ warning) => (
        <p key={warning} role="status" className="hint">
          {warning}
        </p>
      ))}

      <div className="row actions">
        <Button disabled={busy} onClick={onRefresh}>
          Refresh
        </Button>
        <Button disabled={busy || plan !== null} onClick={ask}>
          Refresh with AI
        </Button>
        <Button appearance="accent" disabled={busy} onClick={onNext}>
          Next
        </Button>
        <Button disabled={busy} onClick={onBack}>
          Back
        </Button>
      </div>
      {plan ? (
        <div role="group" aria-labelledby="use-case-plan-title" className="confirm">
          <h3 id="use-case-plan-title">Send to {plan.label}?</h3>
          <p>
            Kodalo will send the text of these {plan.documents.length} documents, with lines that
            look like secrets removed: {plan.documents.join(', ')}. The AI writes the purpose,
            installation methods, capabilities, features and use cases; each one is kept only if its quote is
            in the document.
          </p>
          <p>
            It goes to {plan.label} ({plan.model}). About {plan.input_tokens} tokens sent, and at
            most {plan.max_output_tokens} tokens in the answer.
          </p>
          <div className="row actions">
            <Button appearance="accent" disabled={busy} onClick={proceed}>
              Proceed
            </Button>
            <Button disabled={busy} onClick={() => setPlan(null)}>
              Cancel
            </Button>
          </div>
        </div>
      ) : null}
      {message ? (
        <p role="status" className="hint">
          {message}
        </p>
      ) : null}
    </>
  );
}

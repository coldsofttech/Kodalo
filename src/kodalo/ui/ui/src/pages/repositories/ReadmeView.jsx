import { useState } from 'react';
import { getReadme, planReadmeAnalysis, runReadmeAnalysis } from '../../libs/api.js';
import AiOverlay from '../../components/AiOverlay.jsx';
import { Button } from '../../components/controls.jsx';
import Section from '../../components/Section.jsx';

/** @param {string} value */
const orDash = (value) => value || '-';

/**
 * The Analyze step: what the README and the docs say. They are read without AI first; "Refresh with
 * AI" sends their text to the AI once, after the user has seen what would be sent, and keeps what
 * it finds with a quote.
 *
 * @param {{ repo: any, readme: any, busy: boolean, onRun: (action: () => Promise<void>) => void,
 *   onChange: (readme: any) => void, onRefresh: () => void }} props
 */
export default function ReadmeView({ repo, readme, busy, onRun, onChange, onRefresh }) {
  const [plan, setPlan] = useState(/** @type {any} */ (null));
  const [message, setMessage] = useState('');
  /** True while the AI works, to show the overlay. */
  const [thinking, setThinking] = useState(false);

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
      setThinking(true);
      let result;
      try {
        result = await runReadmeAnalysis(repo.id);
      } finally {
        setThinking(false);
      }
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
      {thinking ? <AiOverlay message="The AI is reading the documents…" /> : null}
      <Section title="Purpose" icon="bi-bullseye">
        {readme.summary || readme.tagline ? (
          <p>{readme.summary || readme.tagline}</p>
        ) : (
          <p className="hint">No introduction was found in the documents.</p>
        )}
      </Section>

      <Section title="Installation" icon="bi-box-arrow-in-down" count={readme.installation.length}>
        {readme.installation.length === 0 ? (
          <p className="hint">No way to install it was found in the documents.</p>
        ) : (
          <table className="checks">
            <caption className="visually-hidden">Installation</caption>
            <thead>
              <tr>
                <th scope="col">Method</th>
                <th scope="col">Command</th>
              </tr>
            </thead>
            <tbody>
              {readme.installation.map((/** @type {any} */ item, /** @type {number} */ index) => (
                <tr key={`${item.method}-${index}`}>
                  <th scope="row">{item.method}</th>
                  <td>
                    {orDash(item.command)}{' '}
                    {item.evidence.file ? (
                      <span className="topic">{item.evidence.file}</span>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>

      <Section title="Capabilities" icon="bi-lightning-charge" count={readme.capabilities.length}>
        {readme.capabilities.length === 0 ? (
          <p className="hint">No features or commands were listed in the documents.</p>
        ) : (
          <table className="checks">
            <caption className="visually-hidden">Capabilities</caption>
            <thead>
              <tr>
                <th scope="col">Capability</th>
                <th scope="col">Description</th>
              </tr>
            </thead>
            <tbody>
              {readme.capabilities.map((/** @type {any} */ item, /** @type {number} */ index) => (
                <tr key={`${item.name}-${index}`}>
                  <th scope="row">
                    {item.name}
                    {item.note ? <span className="topic">{item.note}</span> : null}
                  </th>
                  <td>
                    {orDash(item.description)}{' '}
                    {item.evidence.file ? (
                      <span className="topic">{item.evidence.file}</span>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>

      <Section title="Features" icon="bi-stars" count={readme.features.length}>
        {readme.features.length === 0 ? (
          <p className="hint">
            Features group the capabilities, so the AI writes them. Press Refresh with AI to ask;
            nothing is sent until you agree.
          </p>
        ) : (
          <table className="checks">
            <caption className="visually-hidden">Features</caption>
            <thead>
              <tr>
                <th scope="col">Feature</th>
                <th scope="col">Description</th>
              </tr>
            </thead>
            <tbody>
              {readme.features.map((/** @type {any} */ item, /** @type {number} */ index) => (
                <tr key={`${item.name}-${index}`}>
                  <th scope="row">
                    {item.name}
                    <span className="topic">{item.importance}</span>
                    {item.maturity !== 'unspecified' ? (
                      <span className="topic">{item.maturity}</span>
                    ) : null}
                  </th>
                  <td>
                    {orDash(item.description)}
                    {item.use_cases.length > 0 ? (
                      <div className="hint">Used in: {item.use_cases.join(', ')}.</div>
                    ) : null}
                    {item.claims.length > 0 ? (
                      <div className="hint">
                        Repeat with care:{' '}
                        {item.claims.map((/** @type {any} */ c) => c.text).join('; ')}.
                      </div>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>

      <Section title="Use cases" icon="bi-bullseye" count={readme.use_cases.length}>
        {readme.use_cases.length === 0 ? (
          <p className="hint">
            Use cases need judgement, so the AI writes them. Press Refresh with AI to ask; nothing
            is sent until you agree.
          </p>
        ) : (
          <table className="checks">
            <caption className="visually-hidden">Use cases</caption>
            <thead>
              <tr>
                <th scope="col">Use case</th>
                <th scope="col">Description</th>
              </tr>
            </thead>
            <tbody>
              {readme.use_cases.map((/** @type {any} */ item, /** @type {number} */ index) => (
                <tr key={`${item.title}-${index}`}>
                  <th scope="row">{item.title}</th>
                  <td>{orDash(item.description)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>
      {readme.warnings.map((/** @type {string} */ warning) => (
        <p key={warning} role="status" className="hint">
          {warning}
        </p>
      ))}

      <div className="row actions repo-actions">
        <Button
          appearance="accent"
          label="Refresh"
          title="Refresh"
          disabled={busy}
          onClick={onRefresh}
        >
          <i className="bi bi-arrow-repeat" aria-hidden="true" />
        </Button>
        <Button
          className="ai-button"
          label="Refresh with AI"
          title="Refresh with AI"
          disabled={busy || plan !== null}
          onClick={ask}
        >
          <i className="bi bi-stars" aria-hidden="true" />
        </Button>
      </div>
      {plan ? (
        <div role="group" aria-labelledby="use-case-plan-title" className="confirm">
          <h2 id="use-case-plan-title">Send to {plan.label}?</h2>
          <p>
            Kodalo will send the text of these {plan.documents.length} documents, with lines that
            look like secrets removed: {plan.documents.join(', ')}. The AI writes the purpose,
            installation methods, capabilities, features and use cases; each one is kept only if its
            quote is in the document.
          </p>
          <p>
            It goes to {plan.label} ({plan.model}). About {plan.input_tokens} tokens sent, and at
            most {plan.max_output_tokens} tokens in the answer.
          </p>
          <div className="row actions">
            <Button
              appearance="accent"
              label="Proceed"
              title="Proceed"
              disabled={busy}
              onClick={proceed}
            >
              <i className="bi bi-check-lg" aria-hidden="true" />
            </Button>
            <Button label="Cancel" title="Cancel" disabled={busy} onClick={() => setPlan(null)}>
              <i className="bi bi-x-lg" aria-hidden="true" />
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

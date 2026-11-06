import { useState } from 'react';
import { Button, Select } from '../components/controls.jsx';
import { ideaText, overlapsAvoided } from '../ideas.js';

const FORMATS = { single_image: 'Single image', carousel: 'Carousel' };

/** @param {{ claims: any[] }} props */
function Claims({ claims }) {
  if (claims.length === 0) return null;
  return (
    <ul>
      {claims.map((claim) => (
        <li key={claim.text}>
          {claim.text}
          {claim.needs_review ? ' (check the wording before use)' : ''}
          <span className="hint"> {claim.file ? `${claim.file}: “${claim.quote}”` : ''}</span>
        </li>
      ))}
    </ul>
  );
}

/**
 * @param {{ ideas: any, busy: boolean, brands: any[], brandId: string,
 *   onBrand: (id: string) => void, pick: { idea: string, hook: string } | null,
 *   onPick: (pick: { idea: string, hook: string } | null) => void, onRefresh: () => void,
 *   onNext: () => void, onBack: () => void }} props
 */
export default function IdeasView({
  ideas,
  busy,
  brands,
  brandId,
  onBrand,
  pick,
  onPick,
  onRefresh,
  onNext,
  onBack,
}) {
  const [message, setMessage] = useState('');
  const { strategy, angles, post_ideas: posts } = ideas;
  const title = ideas.focus ? `Post ideas for ${ideas.focus}` : 'Post ideas for the whole tool';
  const hooksOf = (/** @type {any} */ idea) =>
    angles.find((/** @type {any} */ a) => a.id === idea.angle_id)?.hooks ?? [];
  const hookText = (/** @type {any} */ idea, /** @type {string} */ id) =>
    hooksOf(idea).find((/** @type {any} */ h) => h.id === id)?.text ?? '';

  /** @param {any} idea */
  async function copy(idea) {
    const hook = hookText(idea, pick?.idea === idea.id ? pick.hook : idea.hook_id);
    try {
      await navigator.clipboard.writeText(ideaText(idea, hook));
      setMessage(`Copied “${idea.working_title}”.`);
    } catch {
      setMessage('The text could not be copied.');
    }
  }

  return (
    <>
      <h2>{title}</h2>
      {brands.length > 0 ? (
        <Select label="Brand" value={brandId} onChange={onBrand}>
          {brands.map((/** @type {any} */ brand) => (
            <option key={brand.id} value={brand.id}>
              {brand.name}
              {brand.is_default ? ' (default)' : ''}
            </option>
          ))}
        </Select>
      ) : (
        <p className="hint">No brand yet. Create one under Brands to preview posts with it.</p>
      )}
      {strategy.positioning ? <p>{strategy.positioning}</p> : null}
      {strategy.objective ? <p className="hint">Objective: {strategy.objective}</p> : null}

      {ideas.claims_to_avoid.length > 0 ? (
        <div role="group" aria-labelledby="avoid-title" className="confirm">
          <h3 id="avoid-title">Do not repeat without care</h3>
          <ul>
            {ideas.claims_to_avoid.map((/** @type {any} */ claim) => (
              <li key={claim.text}>
                {claim.text} <span className="hint">{claim.reason}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {posts.length === 0 ? (
        <p className="hint">
          The AI found nothing it could support with the saved evidence. Refresh the README analysis
          or choose something else to focus on.
        </p>
      ) : (
        <>
          <h3>Post ideas</h3>
          <p className="hint">Choose the idea to continue with.</p>
        </>
      )}
      <div role="radiogroup" aria-label="Post ideas" className="ideas">
        {posts.map((/** @type {any} */ idea) => {
          const chosen = pick?.idea === idea.id;
          const hookId = chosen ? pick.hook : idea.hook_id;
          const hooks = hooksOf(idea);
          const overlaps = overlapsAvoided(idea, ideas.claims_to_avoid);
          return (
            <div key={idea.id} className="idea">
              <label className="choice">
                <input
                  type="radio"
                  name="post-idea"
                  value={idea.id}
                  checked={chosen}
                  onChange={() => onPick({ idea: idea.id, hook: idea.hook_id })}
                />
                <span className="choice-title">
                  {idea.working_title} <span className="hint">({FORMATS[idea.format]})</span>
                </span>
                <span className="choice-hint">{idea.objective}</span>
                {hookText(idea, hookId) ? (
                  <span className="choice-hint">Hook: {hookText(idea, hookId)}</span>
                ) : null}
              </label>
              {overlaps.length > 0 ? (
                <p className="hint">
                  Careful: this repeats a statement to use with care ({overlaps[0].text}).
                </p>
              ) : null}
              {chosen && hooks.length > 1 ? (
                <Select
                  label="Hook"
                  value={hookId}
                  onChange={(value) => onPick({ idea: idea.id, hook: value })}
                >
                  {hooks.map((/** @type {any} */ hook) => (
                    <option key={hook.id} value={hook.id}>
                      {hook.text}
                    </option>
                  ))}
                </Select>
              ) : null}
              <details>
                <summary>Details: beats, visual and claims</summary>
                <ol>
                  {idea.outline.map((/** @type {string} */ beat) => (
                    <li key={beat}>{beat}</li>
                  ))}
                </ol>
                {idea.visual_concept ? <p className="hint">Visual: {idea.visual_concept}</p> : null}
                <Claims claims={idea.claims_used} />
                {idea.risk_notes ? <p className="hint">Careful: {idea.risk_notes}</p> : null}
                <Button onClick={() => copy(idea)}>Copy</Button>
              </details>
            </div>
          );
        })}
      </div>

      {angles.length > 0 ? (
        <details>
          <summary>Angles and hooks</summary>
          {angles.map((/** @type {any} */ angle) => (
            <section key={angle.id} aria-label={angle.name}>
              <h4>{angle.name}</h4>
              <p>{angle.summary}</p>
              <ul>
                {angle.hooks.map((/** @type {any} */ hook) => (
                  <li key={hook.id}>{hook.text}</li>
                ))}
              </ul>
              {angle.cautions.map((/** @type {string} */ line) => (
                <p key={line} className="hint">
                  Careful: {line}
                </p>
              ))}
            </section>
          ))}
        </details>
      ) : null}

      {ideas.warnings.map((/** @type {string} */ line) => (
        <p key={line} className="hint">
          {line}
        </p>
      ))}
      {message ? (
        <p role="status" className="hint">
          {message}
        </p>
      ) : null}
      <div className="row actions">
        <Button appearance="accent" disabled={busy || !pick} onClick={onNext}>
          Next
        </Button>
        <Button disabled={busy} onClick={onRefresh}>
          Refresh with AI
        </Button>
        <Button disabled={busy} onClick={onBack}>
          Back
        </Button>
      </div>
    </>
  );
}

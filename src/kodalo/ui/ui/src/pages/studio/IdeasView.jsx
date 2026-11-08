import { useState } from 'react';
import { Button, Select } from '../../components/controls.jsx';
import { ideaText } from '../../libs/ideas.js';

const FORMATS = { single_image: 'Single image', carousel: 'Carousel' };
const FORMAT_ICONS = { single_image: 'bi-image', carousel: 'bi-collection' };

/**
 * @param {{ ideas: any, brands: any[], brandId: string,
 *   onBrand: (id: string) => void, pick: { idea: string, hook: string } | null,
 *   onPick: (pick: { idea: string, hook: string } | null) => void }} props
 */
export default function IdeasView({ ideas, brands, brandId, onBrand, pick, onPick }) {
  const [message, setMessage] = useState('');
  const { angles, post_ideas: posts } = ideas;
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
        {posts.map((/** @type {any} */ idea, index) => {
          const chosen = pick?.idea === idea.id;
          const hookId = chosen ? pick.hook : idea.hook_id;
          const hooks = hooksOf(idea);
          return (
            <div key={idea.id} className="idea">
              <label className="idea-pick">
                <span className="idea-head">
                  <input
                    type="radio"
                    name="post-idea"
                    value={idea.id}
                    checked={chosen}
                    onChange={() => onPick({ idea: idea.id, hook: idea.hook_id })}
                  />
                  <span className="idea-num" aria-hidden="true">
                    {index + 1}
                  </span>
                  <span className="idea-format">
                    <i className={`bi ${FORMAT_ICONS[idea.format]}`} aria-hidden="true" />{' '}
                    {FORMATS[idea.format]}
                  </span>
                  {idea.posted ? (
                    <span className="idea-posted">
                      <i className="bi bi-check-circle" aria-hidden="true" /> Posted
                    </span>
                  ) : null}
                </span>
                <span className="idea-title">{idea.working_title}</span>
                <span className="idea-objective">{idea.objective}</span>
                {hookText(idea, hookId) ? (
                  <span className="idea-hook">
                    <i className="bi bi-quote" aria-hidden="true" />
                    <span>Hook: {hookText(idea, hookId)}</span>
                  </span>
                ) : null}
              </label>
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
              <div className="idea-foot">
                <details>
                  <summary>Details: beats and visual</summary>
                  <ol>
                    {idea.outline.map((/** @type {string} */ beat) => (
                      <li key={beat}>{beat}</li>
                    ))}
                  </ol>
                  {idea.visual_concept ? (
                    <p className="hint">Visual: {idea.visual_concept}</p>
                  ) : null}
                </details>
                <Button label="Copy" title="Copy" onClick={() => copy(idea)}>
                  <i className="bi bi-clipboard" aria-hidden="true" />
                </Button>
              </div>
            </div>
          );
        })}
      </div>

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
    </>
  );
}

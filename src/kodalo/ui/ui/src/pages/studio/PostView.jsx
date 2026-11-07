import { useState } from 'react';
import { Button, TextArea, TextField } from '../../components/controls.jsx';
import { useUnsavedGuard } from '../../libs/unsaved.js';

/** @param {any} copy */
function draftOf(copy) {
  return {
    slides: copy.slides.map((/** @type {any} */ slide) => ({ ...slide })),
    opening: copy.caption.opening,
    body: copy.caption.body.join('\n'),
    cta: copy.caption.cta,
    alt: copy.alt_opening.text,
    hashtags: copy.hashtags.join(' '),
  };
}

/**
 * The written post as a list of collapsible items: one for each slide (or the single image) and
 * one for the caption. An item reads as text; its Edit button turns it into fields. The text is
 * saved as a whole, and a new `copy` (after a save or a refresh) replaces the draft.
 * @param {{ copy: any, busy: boolean, onSave: (edits: object) => void }} props
 */
export default function PostView({ copy, busy, onSave }) {
  const [seen, setSeen] = useState(copy);
  const [editing, setEditing] = useState(/** @type {string | null} */ (null));
  const [draft, setDraft] = useState(() => draftOf(copy));
  if (seen !== copy) {
    setSeen(copy);
    setDraft(draftOf(copy));
    setEditing(null);
  }
  const dirty = JSON.stringify(draft) !== JSON.stringify(draftOf(copy));
  useUnsavedGuard(dirty);
  const single = copy.format === 'single_image';

  /** @param {object} patch */
  const change = (patch) => setDraft((current) => ({ ...current, ...patch }));
  /** @param {number} index @param {object} patch */
  const changeSlide = (index, patch) =>
    setDraft((current) => ({
      ...current,
      slides: current.slides.map((/** @type {any} */ slide, /** @type {number} */ at) =>
        at === index ? { ...slide, ...patch } : slide,
      ),
    }));

  const cancel = () => {
    setDraft(draftOf(copy));
    setEditing(null);
  };

  const save = () =>
    onSave({
      slides: draft.slides,
      caption: {
        opening: draft.opening,
        body: draft.body
          .split('\n')
          .map((/** @type {string} */ line) => line.trim())
          .filter(Boolean),
        cta: draft.cta,
      },
      alt_opening: draft.alt,
      hashtags: draft.hashtags.split(/[\s,]+/).filter(Boolean),
    });

  /** The Edit button of an item, or its Save and Cancel while that item is being edited. */
  const actions = (/** @type {string} */ id, /** @type {string} */ name) =>
    editing === id ? (
      <div className="row actions">
        <Button
          appearance="accent"
          label="Save changes"
          title="Save changes"
          disabled={busy || !dirty}
          onClick={save}
        >
          <i className="bi bi-check-lg" aria-hidden="true" />
        </Button>
        <Button label="Cancel" title="Cancel" disabled={busy} onClick={cancel}>
          <i className="bi bi-x-lg" aria-hidden="true" />
        </Button>
      </div>
    ) : (
      <div className="row actions">
        <Button
          label={`Edit ${name}`}
          title={`Edit ${name}`}
          disabled={busy || editing !== null}
          onClick={() => setEditing(id)}
        >
          <i className="bi bi-pencil" aria-hidden="true" />
        </Button>
      </div>
    );

  return (
    <>
      <h2>{single ? 'Image text' : 'Slides'}</h2>
      <div className="post-items">
        {draft.slides.map((/** @type {any} */ slide, /** @type {number} */ index) => {
          const name = single ? 'Image' : `Slide ${index + 1}`;
          const id = `slide-${index}`;
          const saved = copy.slides.at(index);
          return (
            <details key={id} className="post-item">
              <summary>
                <span className="post-item-title">{name}</span>
                {saved?.role ? <span className="idea-format">{saved.role}</span> : null}
              </summary>
              <div className="post-item-body">
                {editing === id ? (
                  <>
                    <TextField
                      label={`${name} headline`}
                      value={slide.headline}
                      maxLength={120}
                      onChange={(value) => changeSlide(index, { headline: value })}
                    />
                    <TextArea
                      label={`${name} text`}
                      value={slide.body}
                      maxLength={300}
                      rows={2}
                      onChange={(value) => changeSlide(index, { body: value })}
                    />
                    <TextField
                      label={`${name} alt text`}
                      value={slide.alt_text}
                      maxLength={200}
                      onChange={(value) => changeSlide(index, { alt_text: value })}
                    />
                  </>
                ) : (
                  <>
                    <p className="post-headline">{saved?.headline}</p>
                    {saved?.body ? <p>{saved.body}</p> : null}
                    {saved?.alt_text ? <p className="hint">Alt text: {saved.alt_text}</p> : null}
                  </>
                )}
                {saved?.visual_note ? <p className="hint">Visual: {saved.visual_note}</p> : null}
                {actions(id, name)}
              </div>
            </details>
          );
        })}

        <details className="post-item">
          <summary>
            <span className="post-item-title">Caption</span>
          </summary>
          <div className="post-item-body">
            {editing === 'caption' ? (
              <>
                <TextField
                  label="Opening line"
                  value={draft.opening}
                  maxLength={200}
                  onChange={(value) => change({ opening: value })}
                />
                <TextArea
                  label="Caption text"
                  value={draft.body}
                  maxLength={1200}
                  rows={4}
                  hint="One line each."
                  onChange={(value) => change({ body: value })}
                />
                <TextField
                  label="Call to action"
                  value={draft.cta}
                  maxLength={200}
                  onChange={(value) => change({ cta: value })}
                />
                <TextField
                  label="Alternative opening"
                  value={draft.alt}
                  maxLength={200}
                  onChange={(value) => change({ alt: value })}
                />
                <TextField
                  label="Hashtags"
                  value={draft.hashtags}
                  maxLength={400}
                  hint="Separated by spaces."
                  onChange={(value) => change({ hashtags: value })}
                />
              </>
            ) : (
              <>
                <p className="post-headline">{copy.caption.opening}</p>
                {copy.caption.body.map((/** @type {string} */ line) => (
                  <p key={line}>{line}</p>
                ))}
                {copy.caption.cta ? <p>{copy.caption.cta}</p> : null}
                {copy.alt_opening.text ? (
                  <p className="hint">Alternative opening: {copy.alt_opening.text}</p>
                ) : null}
                {copy.hashtags.length > 0 ? (
                  <ul className="post-tags" aria-label="Hashtags">
                    {copy.hashtags.map((/** @type {string} */ tag) => (
                      <li key={tag} className="idea-format">
                        {tag}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </>
            )}
            {actions('caption', 'caption')}
          </div>
        </details>
      </div>

      {copy.warnings.map((/** @type {string} */ line) => (
        <p key={line} className="hint">
          {line}
        </p>
      ))}
    </>
  );
}

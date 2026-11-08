// The live preview: sample slides drawn with the draft brand, so every edit shows at once.
// Colors, fonts and sizes come from CSS custom properties set on the root element. They are set
// through the CSSOM (style.setProperty), which Cornea's content security policy allows, unlike an
// inline style attribute in the markup.
import { useCallback, useEffect, useRef, useState } from 'react';
import { logoUrl } from '../libs/api.js';
import { logoFor, previewVariables } from '../libs/brand.js';
import { get } from '../libs/lookup.js';

const SLIDES = ['cover', 'content', 'code', 'quote', 'cta'];
const CAPTIONS = {
  cover: 'Cover',
  content: 'Content',
  code: 'Code',
  quote: 'Quote',
  cta: 'Call to action',
};

/** @param {{ brand: any, data: any, layout: any, mode: 'light' | 'dark', kind: string, index: number, total: number, isLast: boolean, onExpand?: () => void }} props */
function Slide({ brand, data, layout, mode, kind, index, total, isLast, onExpand }) {
  const { logo } = data;
  const logoInfo = logoFor(data, mode);
  const showLogo =
    logoInfo.present &&
    (logo.show_on === 'all' ||
      (logo.show_on === 'first' && index === 0) ||
      (logo.show_on === 'last' && isLast));
  const alt = kind === 'quote' || kind === 'cta';
  return (
    <figure className="slide-figure">
      {onExpand ? (
        <button
          type="button"
          className="slide-expand"
          aria-label={`Full screen: ${get(CAPTIONS, kind)}`}
          title="Full screen"
          onClick={onExpand}
        >
          <i className="bi bi-arrows-fullscreen" aria-hidden="true" />
        </button>
      ) : null}
      <div className="slide-frame">
        <article
          className={`slide slide-${kind}${alt ? ' slide-alt' : ''}`}
          aria-label={`Sample ${kind} slide`}
        >
          {showLogo ? (
            <img
              className={`slide-logo logo-${logo.position}`}
              src={logoUrl(
                brand.id,
                logoInfo.variant === 'dark' ? 'dark' : 'light',
                brand.updated_at,
              )}
              alt=""
            />
          ) : null}
          <div className="slide-body">
            {kind === 'cover' ? (
              <>
                <p className="slide-eyebrow">New release</p>
                <h3 className="slide-title">Your headline goes right here</h3>
                <p className="slide-text">
                  A supporting line in the body font, with a <em>highlighted phrase</em>.
                </p>
              </>
            ) : null}
            {kind === 'content' ? (
              <>
                <h3 className="slide-title">Why it matters</h3>
                <ul className="slide-list">
                  <li>Clear points that are easy to scan</li>
                  <li>
                    One <em>key idea</em> per slide
                  </li>
                  <li>
                    Details in the <strong>body font</strong>
                  </li>
                </ul>
              </>
            ) : null}
            {kind === 'code' ? (
              <>
                <h3 className="slide-title">See it work</h3>
                <pre className="slide-code">
                  <span className="code-prompt">$ </span>kodalo doctor{'\n'}
                  <span className="code-alt">ok</span> all checks passed
                </pre>
              </>
            ) : null}
            {kind === 'quote' ? (
              <>
                <p className="slide-quote">&ldquo;It finally looks like our brand.&rdquo;</p>
                <p className="slide-text">A happy user</p>
              </>
            ) : null}
            {kind === 'cta' ? (
              <>
                <h3 className="slide-title">Try it today</h3>
                <p className="slide-pill">Get started</p>
              </>
            ) : null}
          </div>
          <footer
            className={`slide-footer${showLogo && logo.position === 'bottom_right' ? ' slide-footer-left' : ''}`}
          >
            <span>{layout.footer_text}</span>
            {layout.slide_numbers ? (
              <span>
                {index + 1}/{total}
              </span>
            ) : null}
          </footer>
        </article>
      </div>
      <figcaption>{get(CAPTIONS, kind)}</figcaption>
    </figure>
  );
}

/**
 * One slide at the size of the window, in a modal dialog. Esc closes it (the browser's own
 * behavior), the arrow keys and the buttons step through the slides, and a click outside closes it.
 * @param {{ slide?: any, index: number, count: number, onStep: (delta: number) => void, onClose: () => void, children?: import('react').ReactNode }} props
 */
export function FullScreen({ slide, index, count, onStep, onClose, children }) {
  const dialog = useRef(/** @type {HTMLDialogElement | null} */ (null));
  useEffect(() => {
    const element = dialog.current;
    if (!element) return undefined;
    if (!element.open) {
      if (typeof element.showModal === 'function') element.showModal();
      else element.setAttribute('open', '');
    }
    /** @param {KeyboardEvent} event */
    const onKey = (event) => {
      if (event.key === 'ArrowRight') onStep(1);
      if (event.key === 'ArrowLeft') onStep(-1);
    };
    /** @param {MouseEvent} event */
    const onClick = (event) => {
      if (event.target === element) onClose();
    };
    element.addEventListener('keydown', onKey);
    element.addEventListener('click', onClick);
    return () => {
      element.removeEventListener('keydown', onKey);
      element.removeEventListener('click', onClick);
    };
  }, [onStep, onClose]);
  return (
    <dialog
      ref={dialog}
      className="slide-dialog"
      aria-label="Full screen preview"
      onClose={onClose}
    >
      <div className="slide-dialog-bar">
        <button
          type="button"
          aria-label="Previous slide"
          title="Previous slide"
          disabled={index === 0}
          onClick={() => onStep(-1)}
        >
          <i className="bi bi-chevron-left" aria-hidden="true" />
        </button>
        <span>
          {index + 1} / {count}
        </span>
        <button
          type="button"
          aria-label="Next slide"
          title="Next slide"
          disabled={index === count - 1}
          onClick={() => onStep(1)}
        >
          <i className="bi bi-chevron-right" aria-hidden="true" />
        </button>
        <button type="button" aria-label="Close" title="Close" onClick={onClose}>
          <i className="bi bi-x-lg" aria-hidden="true" />
        </button>
      </div>
      {children ?? <Slide {...slide} />}
    </dialog>
  );
}

/** @param {{ brand: any, data: any, layout: any, canvas: { width: number, height: number } }} props */
export default function Preview({ brand, data, layout, canvas }) {
  const [mode, setMode] = useState(/** @type {'light' | 'dark'} */ ('light'));
  /** Index of the slide shown full screen, or null. */
  const [expanded, setExpanded] = useState(/** @type {number | null} */ (null));
  const closeFull = useCallback(() => setExpanded(null), []);
  const step = useCallback(
    /** @param {number} delta */
    (delta) =>
      setExpanded((i) => (i === null ? i : Math.min(SLIDES.length - 1, Math.max(0, i + delta)))),
    [],
  );
  /** @param {number} index */
  const slideProps = (index) => ({
    brand,
    data,
    layout,
    mode,
    kind: SLIDES.at(index),
    index,
    total: layout.slides_count,
    isLast: index === SLIDES.length - 1,
  });
  const root = useRef(/** @type {HTMLDivElement | null} */ (null));
  const variables = previewVariables(data, mode, layout, canvas);
  const signature = JSON.stringify(variables);
  useEffect(() => {
    const element = root.current;
    if (!element) return;
    for (const [name, value] of Object.entries(JSON.parse(signature))) {
      element.style.setProperty(name, String(value));
    }
  }, [signature]);
  return (
    <section className="preview" aria-label="Preview">
      <div className="preview-head">
        <h2>Preview</h2>
        <div className="segmented" role="group" aria-label="Preview mode">
          {
            /** @type {const} */ (['light', 'dark']).map((value) => (
              <button
                key={value}
                type="button"
                aria-pressed={mode === value}
                onClick={() => setMode(value)}
              >
                {value === 'light' ? 'Light' : 'Dark'}
              </button>
            ))
          }
        </div>
      </div>
      <div ref={root} className="preview-strip">
        {SLIDES.map((kind, index) => (
          <Slide key={kind} {...slideProps(index)} onExpand={() => setExpanded(index)} />
        ))}
        {expanded !== null ? (
          <FullScreen
            slide={slideProps(expanded)}
            index={expanded}
            count={SLIDES.length}
            onStep={step}
            onClose={closeFull}
          />
        ) : null}
      </div>
    </section>
  );
}

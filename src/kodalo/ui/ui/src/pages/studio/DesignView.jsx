// The designed post: each slide is a page the server builds from the saved copy and the design
// plan (a fixed template or the AI's layout), shown in a frame that can run nothing and scaled to
// its card. The same page is what gets posted. Below the slides: the caption and the hashtags.
import { useCallback, useEffect, useRef, useState } from 'react';
import { designSlideUrl } from '../../libs/api.js';
import { FullScreen } from '../../components/preview.jsx';
import InstagramPost from './platforms/instagram/Post.jsx';

/**
 * A slide page in a frame that can run nothing (`sandbox` with no
 * permissions). The page is as big as the canvas and is scaled down to the width of its card.
 * @param {{ url: string, canvas: { width: number, height: number }, label: string }} props
 */
function HtmlSlide({ url, canvas, label }) {
  const frame = useRef(/** @type {HTMLDivElement | null} */ (null));
  useEffect(() => {
    const element = frame.current;
    if (!element) return undefined;
    element.style.setProperty('--canvas-w', String(canvas.width));
    element.style.setProperty('--canvas-h', String(canvas.height));
    const fit = () => {
      if (element.clientWidth) {
        element.style.setProperty('--scale', String(element.clientWidth / canvas.width));
      }
    };
    fit();
    if (typeof ResizeObserver === 'undefined') return undefined;
    const observer = new ResizeObserver(fit);
    observer.observe(element);
    return () => observer.disconnect();
  }, [canvas.width, canvas.height]);
  return (
    <div ref={frame} className="design-html">
      <iframe sandbox="" title={label} src={url} tabIndex={-1} />
    </div>
  );
}

/** @param {any} props */
function DesignSlide({ brand, mode, index, repo, request, version, onExpand }) {
  const name = `Slide ${index + 1}`;
  return (
    <figure className="slide-figure">
      {onExpand ? (
        <button
          type="button"
          className="slide-expand"
          aria-label={`Full screen: ${name}`}
          title="Full screen"
          onClick={onExpand}
        >
          <i className="bi bi-arrows-fullscreen" aria-hidden="true" />
        </button>
      ) : null}
      <div className="slide-frame">
        <HtmlSlide
          url={designSlideUrl(repo.id, request, index, mode, version)}
          canvas={brand.canvas}
          label={name}
        />
      </div>
    </figure>
  );
}

/**
 * @param {{ design: any, copy: any, brand: any, repo: any, request: any, onPosted?: (ideaId: string, posted: boolean) => void }} props
 * `request` is what identifies the post when a slide page is fetched.
 */
export default function DesignView({ design, copy, brand, repo, request, onPosted }) {
  const [mode, setMode] = useState(/** @type {'light' | 'dark'} */ ('light'));
  const [expanded, setExpanded] = useState(/** @type {number | null} */ (null));
  const total = design.slides.length;
  const version = `${design.input_tokens}-${design.output_tokens}`;
  const step = useCallback(
    /** @param {number} delta */
    (delta) =>
      setExpanded((at) => (at === null ? at : Math.min(total - 1, Math.max(0, at + delta)))),
    [total],
  );
  const closeFull = useCallback(() => setExpanded(null), []);
  /** @param {number} index */
  const slideProps = (index) => ({ brand, mode, index, repo, request, version });
  const title = <h2>{copy.format === 'single_image' ? 'Image' : 'Slides'}</h2>;
  return (
    <>
      {brand.canvas.platform_id === 'instagram' ? (
        <InstagramPost
          title={title}
          repo={repo}
          request={request}
          mode={mode}
          slides={total}
          onPosted={onPosted}
        />
      ) : (
        title
      )}
      <div className="post-head">
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
      {design.warnings.map((/** @type {string} */ line) => (
        <p key={line} className="hint">
          {line}
        </p>
      ))}
      <div className="design-grid">
        {design.slides.map((/** @type {any} */ _slide, /** @type {number} */ index) => (
          <DesignSlide key={index} {...slideProps(index)} onExpand={() => setExpanded(index)} />
        ))}
        {expanded !== null ? (
          <FullScreen index={expanded} count={total} onStep={step} onClose={closeFull}>
            <DesignSlide {...slideProps(expanded)} />
          </FullScreen>
        ) : null}
      </div>

      <h2>Caption</h2>
      <section className="design-caption" aria-label="Caption">
        <p className="post-headline">{copy.caption.opening}</p>
        {copy.caption.body.map((/** @type {string} */ line) => (
          <p key={line}>{line}</p>
        ))}
        {copy.caption.cta ? <p>{copy.caption.cta}</p> : null}
        {copy.hashtags.length > 0 ? (
          <ul className="post-tags" aria-label="Hashtags">
            {copy.hashtags.map((/** @type {string} */ tag) => (
              <li key={tag} className="idea-format">
                {tag}
              </li>
            ))}
          </ul>
        ) : null}
      </section>
    </>
  );
}

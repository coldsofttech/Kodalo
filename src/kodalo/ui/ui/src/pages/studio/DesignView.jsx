// The designed post: each slide drawn from the saved copy and the design plan, with the brand's
// colors, fonts and sizes set as CSS custom properties through the CSSOM (the content security
// policy forbids inline styles). The text always comes from the copy; the plan only says how the
// slide is laid out. Below the slides: the caption and the hashtags.
import { useCallback, useEffect, useRef, useState } from 'react';
import { designSlideUrl, designSvgUrl, iconUrl, logoUrl, socialPreviewUrl } from '../../api.js';
import { logoFor, previewVariables } from '../../brand.js';
import { FullScreen } from '../../components/preview.jsx';

/** Which of the preview's slide looks each template uses. */
const LOOKS = {
  hook: 'cover',
  cta: 'cta',
  problem: 'content',
  step: 'content',
  proof: 'content',
  summary: 'content',
  image: 'content',
};

/**
 * The logo of the repository, cut out of its social preview by the box the AI found. The picture
 * is placed with custom properties so the crop needs no inline style.
 * @param {{ repo: any, box: { x: number, y: number, w: number, h: number }, label: string }} props
 */
function LogoCrop({ repo, box, label }) {
  const frame = useRef(/** @type {HTMLSpanElement | null} */ (null));
  const [ratio, setRatio] = useState(1);
  useEffect(() => {
    const element = frame.current;
    if (!element) return;
    element.style.setProperty('--crop-ar', String(ratio));
    element.style.setProperty('--crop-x', String(box.x));
    element.style.setProperty('--crop-y', String(box.y));
    element.style.setProperty('--crop-w', String(box.w));
    element.style.setProperty('--crop-h', String(box.h));
  }, [ratio, box.x, box.y, box.w, box.h]);
  return (
    <span ref={frame} className="design-crop" role="img" aria-label={label}>
      <img
        src={socialPreviewUrl(repo)}
        alt=""
        onLoad={(event) => {
          const { naturalWidth: width, naturalHeight: height } = event.currentTarget;
          if (width && height) setRatio((box.w * width) / (box.h * height));
        }}
      />
    </span>
  );
}

/**
 * A drawing the AI made, as a one-color silhouette in the slide's accent color: the drawing is
 * used as a mask, so it can take the brand's color and never runs or loads anything.
 * @param {{ url: string, label: string }} props
 */
function Drawing({ url, label }) {
  const element = useRef(/** @type {HTMLSpanElement | null} */ (null));
  useEffect(() => {
    element.current?.style.setProperty('--drawing', `url("${url}")`);
  }, [url]);
  return <span ref={element} className="design-drawing" role="img" aria-label={label} />;
}

/**
 * A slide the AI wrote as HTML and CSS, in a frame that can run nothing (`sandbox` with no
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
function Media({ plan, copySlide, repo, box, request, version, index }) {
  const label = copySlide.alt_text || `Slide ${index + 1} picture`;
  if (plan.image_source === 'social_preview') {
    return (
      <div className={`design-media design-fit-${plan.image_fit}`}>
        <img src={socialPreviewUrl(repo)} alt={label} />
      </div>
    );
  }
  if (plan.image_source === 'repo_icon') {
    return (
      <div className="design-media design-media-icon">
        {repo.has_icon ? (
          <img src={iconUrl(repo)} alt={label} />
        ) : box ? (
          <LogoCrop repo={repo} box={box} label={label} />
        ) : null}
      </div>
    );
  }
  if (plan.image_source === 'custom_svg' && plan.has_svg) {
    return (
      <div className="design-media design-media-drawing">
        <Drawing url={designSvgUrl(repo.id, request, index, version)} label={label} />
      </div>
    );
  }
  return null;
}

/** @param {any} props */
function DesignSlide({
  brand,
  mode,
  plan,
  copySlide,
  index,
  total,
  repo,
  box,
  request,
  version,
  onExpand,
}) {
  const { data, layout } = brand;
  const logo = logoFor(data, mode);
  const showLogo =
    logo.present &&
    (data.logo.show_on === 'all' ||
      (data.logo.show_on === 'first' && index === 0) ||
      (data.logo.show_on === 'last' && index === total - 1));
  const look = LOOKS[/** @type {keyof typeof LOOKS} */ (plan.template)] ?? 'content';
  const media = { plan, copySlide, repo, box, request, version, index };
  const name = `Slide ${index + 1}`;
  const written = plan.has_html;
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
        {written ? (
          <HtmlSlide
            url={designSlideUrl(repo.id, request, index, mode, version)}
            canvas={brand.canvas}
            label={name}
          />
        ) : (
          <article
            className={`slide slide-${look}${look === 'cta' ? ' slide-alt' : ''} design-${plan.align} design-${plan.accent} design-template-${plan.template}`}
            aria-label={name}
          >
            {showLogo ? (
              <img
                className={`slide-logo logo-${data.logo.position}`}
                src={logoUrl(
                  brand.id,
                  logo.variant === 'dark' ? 'dark' : 'light',
                  brand.updated_at,
                )}
                alt=""
              />
            ) : null}
            <div className="slide-body">
              {plan.media === 'top' ? <Media {...media} /> : null}
              {plan.template === 'step' ? <span className="design-badge">{index + 1}</span> : null}
              {plan.icon ? (
                <i className={`bi bi-${plan.icon} design-icon`} aria-hidden="true" />
              ) : null}
              <h3 className="slide-title">{copySlide.headline}</h3>
              {copySlide.body ? <p className="slide-text">{copySlide.body}</p> : null}
              {plan.media === 'bottom' ? <Media {...media} /> : null}
            </div>
            <footer
              className={`slide-footer${showLogo && data.logo.position === 'bottom_right' ? ' slide-footer-left' : ''}`}
            >
              <span>{layout.footer_text}</span>
              {layout.slide_numbers ? (
                <span>
                  {index + 1}/{total}
                </span>
              ) : null}
            </footer>
          </article>
        )}
      </div>
    </figure>
  );
}

/**
 * @param {{ design: any, copy: any, brand: any, repo: any, request: any }} props
 * `request` is what identifies the post when a drawing is fetched.
 */
export default function DesignView({ design, copy, brand, repo, request }) {
  const [mode, setMode] = useState(/** @type {'light' | 'dark'} */ ('light'));
  const [expanded, setExpanded] = useState(/** @type {number | null} */ (null));
  const root = useRef(/** @type {HTMLDivElement | null} */ (null));
  const total = design.slides.length;
  const version = `${design.input_tokens}-${design.output_tokens}`;
  const variables = previewVariables(brand.data, mode, brand.layout, brand.canvas);
  const signature = JSON.stringify(variables);
  useEffect(() => {
    const element = root.current;
    if (!element) return;
    for (const [name, value] of Object.entries(JSON.parse(signature))) {
      element.style.setProperty(name, String(value));
    }
  }, [signature]);
  const step = useCallback(
    /** @param {number} delta */
    (delta) =>
      setExpanded((at) => (at === null ? at : Math.min(total - 1, Math.max(0, at + delta)))),
    [total],
  );
  const closeFull = useCallback(() => setExpanded(null), []);
  const box = design.logo_box;
  /** @param {number} index */
  const slideProps = (index) => ({
    brand,
    mode,
    plan: design.slides.at(index),
    copySlide: copy.slides.at(index) ?? { headline: '', body: '', alt_text: '', visual_note: '' },
    index,
    total,
    repo,
    box,
    request,
    version,
  });
  return (
    <>
      <div className="post-head">
        <h2>{copy.format === 'single_image' ? 'Image' : 'Slides'}</h2>
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
      <div ref={root} className="design-grid">
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

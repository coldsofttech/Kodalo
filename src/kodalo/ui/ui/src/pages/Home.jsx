import { Button } from '../components/controls.jsx';

const STEPS = [
  [
    'bi-github',
    'Add a repository',
    'Point Kodalo at a project and let it read what it does.',
    'repositories',
  ],
  [
    'bi-lightbulb',
    'Pick an idea',
    'Choose a post idea and angle suggested for your project.',
    'studio',
  ],
  [
    'bi-pencil-square',
    'Write the copy',
    'Edit the headline, slides, caption and hashtags.',
    'studio',
  ],
  [
    'bi-palette',
    'Design and share',
    'Slides use your brand. Post to Instagram or export them.',
    'studio',
  ],
];

const SHORTCUTS = [
  ['bi-collection', 'Repositories', 'Add or refresh the projects you post about.', 'repositories'],
  ['bi-brush', 'Brands', 'Colors, fonts, logos and layouts for your posts.', 'brands'],
  ['bi-gear', 'Settings', 'Connect GitHub, AI and Instagram, and set logs.', 'settings'],
];

/** @param {{ onOpen: (key: string) => void }} props */
export default function HomePage({ onOpen }) {
  return (
    <div className="home-page">
      <section className="home card" aria-labelledby="home-title">
        <h1 id="home-title">Welcome to Kodalo</h1>
        <p>
          Create posts from your GitHub repositories. Your brands and content stay on this computer,
          and nothing is posted without your approval.
        </p>
        <p>Pick up where you left off, or adjust how your posts look.</p>
        <div className="row">
          <Button appearance="accent" onClick={() => onOpen('studio')}>
            Open Studio
          </Button>
          <Button onClick={() => onOpen('brands')}>Manage brands</Button>
        </div>
      </section>

      <section aria-labelledby="home-steps">
        <h2 id="home-steps">How it works</h2>
        <ol className="home-grid">
          {STEPS.map(([icon, title, text, target], index) => (
            <li key={title} className="card home-tile">
              <button type="button" className="home-link" onClick={() => onOpen(target)}>
                <i className={`bi ${icon}`} aria-hidden="true" />
                <span className="home-title">
                  {index + 1}. {title}
                </span>
                <span className="hint">{text}</span>
              </button>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="home-shortcuts">
        <h2 id="home-shortcuts">Jump to</h2>
        <ul className="home-grid">
          {SHORTCUTS.map(([icon, title, text, target]) => (
            <li key={title} className="card home-tile">
              <button type="button" className="home-link" onClick={() => onOpen(target)}>
                <i className={`bi ${icon}`} aria-hidden="true" />
                <span className="home-title">{title}</span>
                <span className="hint">{text}</span>
              </button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

import { Button } from '../components/controls.jsx';

/** @param {{ onOpen: (key: string) => void }} props */
export default function HomePage({ onOpen }) {
  return (
    <section className="home card" aria-labelledby="home-title">
      <h1 id="home-title">Welcome to Kodalo</h1>
      <p>
        Create posts from your GitHub repositories. Your brands and content stay on this computer,
        and nothing is posted without your approval.
      </p>
      <p>Pick up where you left off, or adjust how your posts look.</p>
      <Button appearance="accent" onClick={() => onOpen('studio')}>
        Open Studio
      </Button>
      <Button onClick={() => onOpen('brands')}>Manage brands</Button>
    </section>
  );
}

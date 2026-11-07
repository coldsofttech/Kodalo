import { useEffect, useState } from 'react';
import { getAiIdeaCount, setAiIdeaCount } from '../../../libs/api.js';
import { Button, TextField } from '../../../components/controls.jsx';
import { useUnsavedGuard } from '../../../libs/unsaved.js';

const MIN = 1;
const MAX = 20;

/** How many post ideas Studio asks the AI for each time. */
export default function AiIdeaCount() {
  const [saved, setSaved] = useState(/** @type {number | null} */ (null));
  const [text, setText] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    getAiIdeaCount().then(
      (found) => {
        if (!alive) return;
        setSaved(found.idea_count);
        setText(String(found.idea_count));
      },
      (failure) => alive && setError(failure.message),
    );
    return () => {
      alive = false;
    };
  }, []);

  const count = Number(text);
  const valid = text.trim() !== '' && Number.isInteger(count) && count >= MIN && count <= MAX;
  const changed = saved !== null && text !== String(saved);
  useUnsavedGuard(changed);

  async function save() {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const found = await setAiIdeaCount(count);
      setSaved(found.idea_count);
      setText(String(found.idea_count));
      setMessage('Saved.');
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Something went wrong.');
    } finally {
      setBusy(false);
    }
  }

  if (saved === null && !error) return <p>Loading…</p>;
  return (
    <div className="ai-idea-count">
      <TextField
        label="Post ideas per request"
        value={text}
        onChange={setText}
        maxLength={2}
        invalid={text !== '' && !valid}
        hint={`From ${MIN} to ${MAX}. Asking again adds new ideas to the saved ones; a bigger number costs more tokens.`}
      />
      {error ? (
        <p role="alert" className="alert">
          {error}
        </p>
      ) : null}
      {message ? (
        <p role="status" className="notice">
          {message}
        </p>
      ) : null}
      <div className="row actions">
        <Button
          appearance="accent"
          disabled={busy || !valid || !changed}
          onClick={save}
          label="Save post ideas"
          title="Save post ideas"
        >
          <i className="bi bi-floppy" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}

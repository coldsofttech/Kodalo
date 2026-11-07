// State shared by the Canvases, Palettes and Layouts pages: the list, the messages, and a way to
// run a change and then reload the list and tell the rest of the app.
import { useCallback, useEffect, useRef, useState } from 'react';

/** @param {unknown} error @param {string} fallback */
export const errorText = (error, fallback) => (error instanceof Error ? error.message : fallback);

/**
 * @param {() => Promise<any[]>} load fetches the list
 * @param {string} loadFailure what to say when the list cannot be loaded
 * @param {number} revision reload when this changes (something else changed the list)
 * @param {(() => void) | undefined} onChange runs after this page changed something
 */
export function useCatalog(load, loadFailure, revision, onChange) {
  const [items, setItems] = useState(/** @type {any[] | null} */ (null));
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const loader = useRef(load);
  useEffect(() => {
    loader.current = load;
  });

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const list = await loader.current();
        if (alive) setItems(list);
      } catch (failure) {
        if (!alive) return;
        setItems((previous) => previous ?? []);
        setError(errorText(failure, loadFailure));
      }
    })();
    return () => {
      alive = false;
    };
  }, [revision, loadFailure]);

  /**
   * Run a call that changes things. Returns whether it worked.
   * @param {() => Promise<unknown>} task
   * @param {string} done the notice to show when it worked
   */
  const act = useCallback(
    async (task, done) => {
      setBusy(true);
      setError('');
      setNotice('');
      try {
        await task();
        setItems(await loader.current());
        setNotice(done);
        onChange?.();
        return true;
      } catch (failure) {
        setError(errorText(failure, 'That did not work.'));
        return false;
      } finally {
        setBusy(false);
      }
    },
    [onChange],
  );

  return { items, error, notice, busy, act, setError };
}

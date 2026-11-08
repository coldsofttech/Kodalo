import { createContext, useCallback, useContext, useEffect, useId, useState } from 'react';

/**
 * How a page tells the app it holds unsaved edits. The app provides the function; without one (in
 * a test that renders a page alone) nothing is reported.
 * @type {import('react').Context<((id: string, dirty: boolean) => void) | null>}
 */
export const UnsavedContext = createContext(
  /** @type {((id: string, dirty: boolean) => void) | null} */ (null),
);

/**
 * Report whether this part of a page holds unsaved edits. While `dirty` is true, leaving the page
 * asks first; a page that reports nothing is left without asking, and starts fresh on its next
 * visit.
 * @param {boolean} dirty
 */
export function useUnsavedGuard(dirty) {
  const report = useContext(UnsavedContext);
  const id = useId();
  useEffect(() => {
    report?.(id, dirty);
    return () => report?.(id, false);
  }, [report, id, dirty]);
}

/**
 * Track whether `values` differ from what was last loaded or saved, and report it. Call the
 * returned function with the loaded or saved values (in the same shape as `values`) whenever the
 * form is filled from the server or saved.
 * @template T
 * @param {T} values the form's current values
 * @returns {(saved: T) => void} remembers `saved` as the form's saved state
 */
export function useSavedValues(values) {
  const [baseline, setBaseline] = useState(/** @type {string | null} */ (null));
  useUnsavedGuard(baseline !== null && JSON.stringify(values) !== baseline);
  return useCallback(
    /** @param {T} saved */
    (saved) => setBaseline(JSON.stringify(saved)),
    [],
  );
}

import { useEffect, useRef } from 'react';
import { socialPreviewUrl } from '../api.js';

/**
 * A repository's social preview image at the size of the window, in a modal dialog like the full
 * screen slide preview: Esc, the close button or a click outside closes it.
 * @param {{ repo: any, onClose: () => void }} props
 */
export default function SocialPreviewDialog({ repo, onClose }) {
  const dialog = useRef(/** @type {HTMLDialogElement | null} */ (null));
  useEffect(() => {
    const element = dialog.current;
    if (!element) return undefined;
    if (!element.open) {
      if (typeof element.showModal === 'function') element.showModal();
      else element.setAttribute('open', '');
    }
    /** @param {MouseEvent} event */
    const onClick = (event) => {
      if (event.target === element) onClose();
    };
    element.addEventListener('click', onClick);
    return () => element.removeEventListener('click', onClick);
  }, [onClose]);
  return (
    <dialog
      ref={dialog}
      className="slide-dialog image-dialog"
      aria-label="Social preview"
      onClose={onClose}
    >
      <div className="slide-dialog-bar">
        <button type="button" aria-label="Close" title="Close" onClick={onClose}>
          <i className="bi bi-x-lg" aria-hidden="true" />
        </button>
      </div>
      <img
        className="image-dialog-image"
        src={socialPreviewUrl(repo)}
        alt={`Social preview of ${repo.owner}/${repo.name}`}
      />
    </dialog>
  );
}

import { useRef } from 'react';
import { Button } from './controls.jsx';

/**
 * A button that lets the user pick an exported JSON file.
 * @param {{ label: string, what: string, disabled?: boolean, onImport: (file: File) => void }} props
 */
export default function ImportButton({ label, what, disabled, onImport }) {
  const input = useRef(/** @type {HTMLInputElement | null} */ (null));
  return (
    <>
      <input
        ref={input}
        type="file"
        accept="application/json,.json"
        className="visually-hidden"
        aria-label={`Choose a ${what} file to import`}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onImport(file);
          event.target.value = '';
        }}
      />
      <Button appearance="outline" disabled={disabled} onClick={() => input.current?.click()}>
        {label}
      </Button>
    </>
  );
}

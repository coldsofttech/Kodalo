// Small React wrappers around the Fluent UI Web Components. A custom element reports changes with
// DOM events and keeps its value as a property, so each wrapper wires both ends.
import { useEffect, useId, useRef } from 'react';

/**
 * Keep a custom element's property in step with React state and report its `events`.
 * @param {string} property
 * @param {unknown} value
 * @param {string[]} events
 * @param {(element: any) => void} onEvent
 */
function useElement(property, value, events, onEvent) {
  const ref = useRef(/** @type {any} */ (null));
  const handler = useRef(onEvent);
  useEffect(() => {
    handler.current = onEvent;
  });
  useEffect(() => {
    const element = ref.current;
    if (element && element[property] !== value) element[property] = value;
  }, [property, value]);
  useEffect(() => {
    const element = ref.current;
    const listener = () => handler.current(element);
    for (const name of events) element.addEventListener(name, listener);
    return () => {
      for (const name of events) element.removeEventListener(name, listener);
    };
  }, [events]);
  return ref;
}

const TEXT_EVENTS = ['input', 'change'];
const CHANGE_EVENTS = ['change'];

/** @param {{ label: string, value: string, onChange: (value: string) => void, hint?: string, maxLength?: number, disabled?: boolean, invalid?: boolean, hideLabel?: boolean, type?: 'text' | 'password' }} props */
export function TextField({
  label,
  value,
  onChange,
  hint,
  maxLength,
  disabled,
  invalid,
  hideLabel,
  type,
}) {
  const ref = useElement('value', value, TEXT_EVENTS, (el) => onChange(String(el.value ?? '')));
  return (
    <div className="field">
      <fluent-text-field
        ref={ref}
        aria-label={label}
        aria-invalid={invalid ? 'true' : undefined}
        maxlength={maxLength}
        disabled={disabled}
        type={type}
        autocomplete={type === 'password' ? 'off' : undefined}
        appearance="outline"
      >
        {hideLabel ? null : label}
      </fluent-text-field>
      {hint ? <p className="hint">{hint}</p> : null}
    </div>
  );
}

/** @param {{ label: string, value: number, min: number, max: number, onChange: (value: number) => void, hint?: string }} props */
export function NumberField({ label, value, min, max, onChange, hint }) {
  const ref = useElement('value', String(value), TEXT_EVENTS, (el) => {
    const number = Number.parseInt(el.value, 10);
    if (Number.isFinite(number)) onChange(Math.min(max, Math.max(min, number)));
  });
  return (
    <div className="field">
      <fluent-number-field
        ref={ref}
        aria-label={label}
        min={min}
        max={max}
        step={1}
        appearance="outline"
        hide-step=""
      >
        {label}
      </fluent-number-field>
      {hint ? <p className="hint">{hint}</p> : null}
    </div>
  );
}

/** @param {{ label: string, checked: boolean, onChange: (checked: boolean) => void }} props */
export function Switch({ label, checked, onChange }) {
  const ref = useElement('checked', checked, CHANGE_EVENTS, (el) => onChange(Boolean(el.checked)));
  return (
    <fluent-switch ref={ref} aria-label={label}>
      {label}
    </fluent-switch>
  );
}

/** @param {{ children: import('react').ReactNode, onClick?: () => void, appearance?: 'accent' | 'neutral' | 'outline' | 'stealth', disabled?: boolean, label?: string, danger?: boolean }} props */
export function Button({ children, onClick, appearance = 'neutral', disabled, label, danger }) {
  return (
    <fluent-button
      appearance={appearance}
      disabled={disabled}
      aria-label={label}
      danger={danger ? '' : undefined}
      onClick={disabled ? undefined : onClick}
    >
      {children}
    </fluent-button>
  );
}

/**
 * A native select, styled to match. It handles the long, grouped font lists better than a
 * custom element would.
 * @param {{ label: string, value: string, onChange: (value: string) => void, children: import('react').ReactNode }} props
 */
export function Select({ label, value, onChange, children }) {
  return (
    <label className="field select">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {children}
      </select>
    </label>
  );
}

/**
 * A text box that is also a dropdown: it suggests `options` but accepts any text. A native input
 * with a datalist, like Select, so it follows the same look and keyboard behavior.
 * @param {{ label: string, value: string, onChange: (value: string) => void, options: string[], maxLength?: number }} props
 */
export function ComboBox({ label, value, onChange, options, maxLength }) {
  const list = useId();
  return (
    <label className="field select">
      <span>{label}</span>
      <input
        type="text"
        list={list}
        value={value}
        maxLength={maxLength}
        autoComplete="off"
        onChange={(event) => onChange(event.target.value)}
      />
      <datalist id={list}>
        {options.map((option) => (
          <option key={option} value={option} />
        ))}
      </datalist>
    </label>
  );
}

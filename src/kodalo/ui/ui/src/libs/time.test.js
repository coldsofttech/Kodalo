import { describe, expect, it } from 'vitest';
import { localTime } from './time.js';

describe('localTime', () => {
  it('shows a dash when there is no time', () => {
    expect(localTime(null)).toBe('-');
    expect(localTime(undefined)).toBe('-');
    expect(localTime('')).toBe('-');
  });

  it('formats a date in the local format', () => {
    const value = '2026-11-01T09:00:00+00:00';
    expect(localTime(value)).toBe(new Date(value).toLocaleString());
  });

  it('keeps text that is not a date', () => {
    expect(localTime('yesterday')).toBe('yesterday');
  });
});

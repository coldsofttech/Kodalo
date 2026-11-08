import { describe, expect, it } from 'vitest';
import { get } from './lookup.js';

describe('get', () => {
  it('returns an own property', () => {
    expect(get({ a: 1, b: undefined }, 'a')).toBe(1);
    expect(get({ a: 1, b: undefined }, 'b')).toBeUndefined();
  });

  it('finds nothing for inherited keys', () => {
    for (const key of ['constructor', 'toString', '__proto__', 'hasOwnProperty']) {
      expect(get({}, key)).toBeUndefined();
    }
  });

  it('finds nothing in a missing object or for a missing key', () => {
    expect(get(null, 'a')).toBeUndefined();
    expect(get(undefined, 'a')).toBeUndefined();
    expect(get({ a: 1 }, 'b')).toBeUndefined();
  });

  it('reads an own key that is named like an inherited one', () => {
    expect(get(Object.fromEntries([['constructor', 'mine']]), 'constructor')).toBe('mine');
  });
});

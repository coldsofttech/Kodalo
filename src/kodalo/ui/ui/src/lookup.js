// Reading a value by a key that is not a literal. Only an object's own properties are returned,
// so a key such as "constructor" or "__proto__" finds nothing instead of something inherited.

/**
 * @param {any} object
 * @param {string} key
 * @returns {any}
 */
export function get(object, key) {
  return object !== null && object !== undefined && Object.hasOwn(object, key)
    ? Reflect.get(object, key)
    : undefined;
}

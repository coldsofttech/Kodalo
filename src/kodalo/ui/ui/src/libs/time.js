/**
 * A timestamp in the user's own time zone and format; the text itself if it is not a date.
 * @param {string | null | undefined} value
 */
export function localTime(value) {
  if (!value) return '-';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

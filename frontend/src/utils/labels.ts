/**
 * One way of writing a column heading, wherever it comes from.
 *
 * Headings arrive from three places — the fruit config ("Less Colour"), the
 * online reader ("Stem crack", "ROTTEN SPOT") and the surveyor typing one in —
 * and used to be shown exactly as received, so one table mixed three styles.
 * Every heading is shown in Title Case; short joining words stay lower case,
 * and anything already written as an abbreviation (pcs, kg, XF) is left alone.
 */
const SMALL_WORDS = new Set(['of', 'and', 'or', 'the', 'in', 'on', 'to', 'with', 'per']);

export function columnTitle(raw: string): string {
  const text = (raw || '').replace(/\s+/g, ' ').trim();
  if (!text) return '';
  return text
    .split(' ')
    .map((word, i) => {
      // Units in brackets, and short all-caps codes, are written as they are.
      if (/^\(.*\)$/.test(word) || /^[A-Z0-9]{1,3}$/.test(word)) return word;
      const lower = word.toLowerCase();
      if (i > 0 && SMALL_WORDS.has(lower)) return lower;
      return lower.charAt(0).toUpperCase() + lower.slice(1);
    })
    .join(' ');
}

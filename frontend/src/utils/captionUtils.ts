/**
 * Robust Caption Auto-Numbering & Formatting Utilities
 * Handles all prefix formats, re-ordering, custom keywords, and offset start numbers.
 */

/**
 * Strip any existing photo numbering prefix from a caption string.
 * Examples:
 *   "Photo 1: Container exterior" -> "Container exterior"
 *   "Photo No. 5 — Cargo stowage" -> "Cargo stowage"
 *   "Photo 3 - Seal intact" -> "Seal intact"
 *   "(Photo 4) Pulp reading" -> "Pulp reading"
 *   "Survey Photo No. 12: Sound produce" -> "Sound produce"
 *   "Image 2: Fruit inspection" -> "Fruit inspection"
 *   "Photo 4" -> ""
 *   "Container exterior" -> "Container exterior"
 */
export function stripPhotoPrefix(caption: string): string {
  if (!caption) return '';

  const trimmed = caption.trim();

  // If the caption is purely a photo numbering label like "Photo 4", "Photo No. 9", "(Photo 3)", etc.
  if (/^\(?\s*(?:survey\s+)?(?:photo|image|pic|img)\s*(?:no\.?)?\s*\d+\s*\)?[:\-\—\.\,\s]*$/i.test(trimmed)) {
    return '';
  }

  // Strip leading prefix followed by separator (: - — . , or space)
  return trimmed.replace(
    /^\s*\(?\s*(?:survey\s+)?(?:photo|image|pic|img)\s*(?:no\.?)?\s*\d+\s*\)?\s*[:\-\—\.\,\s]\s*/i,
    ''
  ).trim();
}

export interface AutoNumberOptions {
  keyword?: string;     // default: 'Photo' or 'Survey Photo No.'
  separator?: string;   // default: ': ' or ' — '
  startNum?: number;    // default: 1
  mode?: 'prefix' | 'number_only' | 'strip';
}

/**
 * Formats a caption with the correct sequential photo number.
 * Automatically cleans any old number prefix and applies the new number.
 */
export function formatAutoCaption(
  existingCaption: string,
  index: number,
  options: AutoNumberOptions = {}
): string {
  const {
    keyword = 'Photo',
    separator = ': ',
    startNum = 1,
    mode = 'prefix',
  } = options;

  const currentNumber = index + startNum;
  const rawText = stripPhotoPrefix(existingCaption || '');

  if (mode === 'strip') {
    return rawText;
  }

  if (mode === 'number_only' || !rawText) {
    return `${keyword} ${currentNumber}`;
  }

  return `${keyword} ${currentNumber}${separator}${rawText}`;
}

/**
 * Re-numbers an entire array of captions, preserving observation descriptions
 * while ensuring sequential, gap-free numbering.
 */
export function autoNumberCaptionsList(
  captions: string[],
  options: AutoNumberOptions = {}
): string[] {
  return captions.map((cap, idx) => formatAutoCaption(cap, idx, options));
}


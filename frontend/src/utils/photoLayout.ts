/**
 * How the survey photographs are laid out in the report — the same rules as
 * backend/app/render/photo_layout.py, so the preview shows what Word prints.
 *
 * The layout is the client's own photo tool (Auto-on-render, Pro mode), as
 * measured in his reports: A4, two across, 8.2 x 5.6 cm each, no border,
 * "Survey Photo No. N" under each, 8 to a page (sometimes 6).
 */

export interface PhotoLayout {
  per_page: 8 | 6;
  border: boolean;
  border_color: string;
  caption_keyword: string;
  number_from: number;
  caption_font: string;
  caption_size: number;
  caption_color: string;
  quality: 'original' | 'high' | 'balanced' | 'small';
  landscape: boolean;
  show_heading: boolean;
}

export const PHOTO_DEFAULTS: PhotoLayout = {
  per_page: 8,
  border: false,
  border_color: '000000',
  caption_keyword: 'Survey Photo No.',
  number_from: 1,
  caption_font: 'Arial',
  caption_size: 11,
  caption_color: '000000',
  quality: 'balanced',
  landscape: true,
  show_heading: false,
};

export const KEYWORDS = ['Survey Photo No.', 'QC Inspection Photo No.'];
export const FONTS = ['Arial', 'Calibri', 'Times New Roman', 'Georgia', 'Verdana'];
export const FONT_SIZES = [8, 9, 10, 11, 12, 14, 16, 18, 20];
export const FONT_COLORS = [
  { name: 'Black', value: '000000' },
  { name: 'White', value: 'FFFFFF' },
  { name: 'Navy Blue', value: '000080' },
  { name: 'Dark Gray', value: '404040' },
  { name: 'Dark Green', value: '006400' },
];
export const BORDER_COLORS = [
  { name: 'Black', value: '000000' },
  { name: 'Gray', value: '808080' },
  { name: 'Navy', value: '000080' },
  { name: 'Brown', value: '8B4513' },
];
export const QUALITIES: { key: PhotoLayout['quality']; label: string; note: string }[] = [
  { key: 'original', label: 'Original', note: 'Full size — large Word file' },
  { key: 'high', label: 'High', note: '~2 MB a photo' },
  { key: 'balanced', label: 'Balanced', note: '~1 MB a photo' },
  { key: 'small', label: 'Small', note: '~500 KB a photo' },
];

/** The photo box in the report: 310 x 210 px at 96 dpi. */
export const PHOTO_W_CM = (310 * 2.54) / 96;
export const PHOTO_H_CM = (210 * 2.54) / 96;

export function layoutOf(block: any): PhotoLayout {
  const raw = block?.layout || {};
  const out: PhotoLayout = { ...PHOTO_DEFAULTS };
  if (Number(raw.per_page) === 6 || Number(raw.per_page) === 8) out.per_page = Number(raw.per_page) as 8 | 6;
  if (FONTS.includes(raw.caption_font)) out.caption_font = raw.caption_font;
  if (FONT_SIZES.includes(Number(raw.caption_size))) out.caption_size = Number(raw.caption_size);
  const hex = (v: any) => String(v || '').toUpperCase().replace(/^#/, '');
  if (FONT_COLORS.some((c) => c.value === hex(raw.caption_color))) out.caption_color = hex(raw.caption_color);
  if (BORDER_COLORS.some((c) => c.value === hex(raw.border_color))) out.border_color = hex(raw.border_color);
  if (QUALITIES.some((q) => q.key === raw.quality)) out.quality = raw.quality;
  (['border', 'landscape', 'show_heading'] as const).forEach((k) => {
    if (typeof raw[k] === 'boolean') out[k] = raw[k];
  });
  const kw = String(raw.caption_keyword || '').split(/\s+/).filter(Boolean).join(' ');
  if (kw) out.caption_keyword = kw.slice(0, 40);
  const n = parseInt(raw.number_from, 10);
  if (n >= 1 && n <= 9999) out.number_from = n;
  return out;
}

const PREFIX_ONLY = /^\(?\s*(?:survey\s+|qc\s+inspection\s+)?(?:photo|image|pic|img)\s*(?:no\.?)?\s*\d+\s*\)?[:\-—.,\s]*$/i;
const PREFIX = /^\s*\(?\s*(?:survey\s+|qc\s+inspection\s+)?(?:photo|image|pic|img)\s*(?:no\.?)?\s*\d+\s*\)?\s*[:\-—.,\s]\s*/i;

/** Caption text without a photo number typed into it; numbers are added when the report is made. */
export function stripNumber(text: string): string {
  const t = (text || '').trim();
  if (!t || PREFIX_ONLY.test(t)) return '';
  return t.replace(PREFIX, '').trim();
}

export function photoCaption(layout: PhotoLayout, number: number, text = ''): string {
  const body = stripNumber(text);
  const head = `${layout.caption_keyword} ${number}`;
  return body ? `${head} — ${body}` : head;
}

/** Photos split into report pages; a heading on the first page takes one row. */
export function photoPages<T>(photos: T[], layout: PhotoLayout): T[][] {
  if (!photos.length) return [];
  const first = layout.show_heading ? layout.per_page - 2 : layout.per_page;
  const pages: T[][] = [photos.slice(0, first)];
  for (let i = first; i < photos.length; i += layout.per_page) pages.push(photos.slice(i, i + layout.per_page));
  return pages.filter((p) => p.length);
}

/** Where a photo's image is served; the address changes when the photo is turned. */
export function photoUrl(reportId: string | undefined, assetId: string, asset: any): string {
  if (asset?.url) return asset.url;
  return reportId ? `/api/reports/${reportId}/assets/${assetId}/image` : '';
}

import React from 'react';
import { LayoutGrid } from 'lucide-react';
import {
  BORDER_COLORS,
  FONT_COLORS,
  FONT_SIZES,
  FONTS,
  KEYWORDS,
  PhotoLayout,
  photoCaption,
  QUALITIES,
} from '../../utils/photoLayout';

interface Props {
  layout: PhotoLayout;
  onChange: (next: PhotoLayout) => void;
}

const selectCls =
  'w-full px-2.5 py-1.5 bg-white border border-gray-200 rounded-lg text-xs font-medium focus:ring-1 focus:ring-indigo-500 outline-hidden';
const labelCls = 'block text-[11px] font-semibold text-gray-600 mb-1';

/**
 * The photo tool's options, kept on the photo section and used by the Word
 * file and the preview. Starts as the client's own layout: 8 to a page, no
 * border, "Survey Photo No. N" in Arial 11.
 */
export const PhotoLayoutPanel: React.FC<Props> = ({ layout, onChange }) => {
  const set = (patch: Partial<PhotoLayout>) => onChange({ ...layout, ...patch });
  const custom = !KEYWORDS.includes(layout.caption_keyword);

  return (
    <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl space-y-3" data-testid="photo-layout-panel">
      <div className="flex items-center gap-2">
        <LayoutGrid className="w-4 h-4 text-indigo-600" />
        <span className="text-xs font-bold text-gray-800">How the photos look in the report</span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div>
          <label className={labelCls}>Photos per page</label>
          <select
            aria-label="Photos per page"
            value={layout.per_page}
            onChange={(e) => set({ per_page: Number(e.target.value) as 8 | 6 })}
            className={selectCls}
          >
            <option value={8}>8 (4 rows of 2)</option>
            <option value={6}>6 (3 rows of 2)</option>
          </select>
        </div>

        <div>
          <label className={labelCls}>Caption words</label>
          <select
            aria-label="Caption words"
            value={custom ? 'custom' : layout.caption_keyword}
            onChange={(e) =>
              set({ caption_keyword: e.target.value === 'custom' ? 'Photo No.' : e.target.value })
            }
            className={selectCls}
          >
            {KEYWORDS.map((k) => (
              <option key={k} value={k}>{k}</option>
            ))}
            <option value="custom">Your own words…</option>
          </select>
          {custom && (
            <input
              aria-label="Your own caption words"
              value={layout.caption_keyword}
              onChange={(e) => set({ caption_keyword: e.target.value })}
              placeholder="e.g. Cargo Photo No."
              className="w-full mt-1.5 px-2.5 py-1 bg-white border border-gray-200 rounded-lg text-xs outline-hidden"
            />
          )}
        </div>

        <div>
          <label className={labelCls}>First number</label>
          <input
            aria-label="First photo number"
            type="number"
            min={1}
            value={layout.number_from}
            onChange={(e) => set({ number_from: Math.max(1, parseInt(e.target.value, 10) || 1) })}
            className={selectCls}
          />
        </div>

        <div>
          <label className={labelCls}>Photo quality</label>
          <select
            aria-label="Photo quality"
            value={layout.quality}
            onChange={(e) => set({ quality: e.target.value as PhotoLayout['quality'] })}
            className={selectCls}
          >
            {QUALITIES.map((q) => (
              <option key={q.key} value={q.key}>{q.label} — {q.note}</option>
            ))}
          </select>
        </div>

        <div>
          <label className={labelCls}>Caption font</label>
          <select
            aria-label="Caption font"
            value={layout.caption_font}
            onChange={(e) => set({ caption_font: e.target.value })}
            className={selectCls}
          >
            {FONTS.map((f) => (
              <option key={f} value={f}>{f}</option>
            ))}
          </select>
        </div>

        <div>
          <label className={labelCls}>Caption size</label>
          <select
            aria-label="Caption size"
            value={layout.caption_size}
            onChange={(e) => set({ caption_size: Number(e.target.value) })}
            className={selectCls}
          >
            {FONT_SIZES.map((s) => (
              <option key={s} value={s}>{s} pt</option>
            ))}
          </select>
        </div>

        <div>
          <label className={labelCls}>Caption colour</label>
          <select
            aria-label="Caption colour"
            value={layout.caption_color}
            onChange={(e) => set({ caption_color: e.target.value })}
            className={selectCls}
          >
            {FONT_COLORS.map((c) => (
              <option key={c.value} value={c.value}>{c.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label className={labelCls}>Border</label>
          <div className="flex items-center gap-2">
            <label className="inline-flex items-center gap-1.5 cursor-pointer select-none">
              <input
                type="checkbox"
                aria-label="Border around each photo"
                checked={layout.border}
                onChange={(e) => set({ border: e.target.checked })}
              />
              <span>On</span>
            </label>
            <select
              aria-label="Border colour"
              value={layout.border_color}
              disabled={!layout.border}
              onChange={(e) => set({ border_color: e.target.value })}
              className={`${selectCls} disabled:opacity-40`}
            >
              {BORDER_COLORS.map((c) => (
                <option key={c.value} value={c.value}>{c.name}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-gray-700">
        <label className="inline-flex items-center gap-1.5 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={layout.landscape}
            onChange={(e) => set({ landscape: e.target.checked })}
          />
          Turn upright photos sideways when adding them
        </label>
        <label className="inline-flex items-center gap-1.5 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={layout.show_heading}
            onChange={(e) => set({ show_heading: e.target.checked })}
          />
          Heading above the photos
        </label>
        <span className="text-[11px] text-gray-500 font-mono bg-white border border-gray-200 px-2 py-1 rounded-lg">
          Caption:{' '}
          <span
            style={{
              fontFamily: `'${layout.caption_font}', sans-serif`,
              color: layout.caption_color === 'FFFFFF' ? '#9ca3af' : `#${layout.caption_color}`,
            }}
          >
            {photoCaption(layout, layout.number_from)}
          </span>
        </span>
      </div>
    </div>
  );
};

export default PhotoLayoutPanel;

import React from 'react';
import { Camera } from 'lucide-react';
import { layoutOf, photoCaption, photoUrl, PHOTO_H_CM, PHOTO_W_CM } from '../../../utils/photoLayout';

export interface PreviewPhoto {
  number: number;
  caption: string;
  assetId?: string;
  imagePath?: string;
}

export interface PhotoPlateBlockProps {
  block: any;
  computed?: any;
  assets?: Record<string, any>;
  reportId?: string;
  /** One page of photos, already numbered and captioned. */
  photoSlice?: PreviewPhoto[];
  /** Show the section heading (first photo page only, when ticked). */
  showHeading?: boolean;
}

/** Every photo in the block, numbered and captioned as the report prints them. */
export function previewPhotos(block: any, assets: Record<string, any>, reportId?: string): PreviewPhoto[] {
  const lay = layoutOf(block);
  const shift = lay.number_from - 1;
  const computedGroups = block?._computed?.groups || {};
  const out: PreviewPhoto[] = [];
  (block?.groups || []).forEach((g: any) => {
    const ids: string[] = g.asset_ids || [];
    const numbers: number[] = computedGroups[g.id || '']?.numbers || ids.map((_, i) => out.length + i + 1);
    ids.forEach((aid, idx) => {
      const n = (numbers[idx] || out.length + 1) + shift;
      out.push({
        number: n,
        caption: photoCaption(lay, n, g.observation || ''),
        assetId: aid,
        imagePath: photoUrl(reportId, aid, assets[aid]),
      });
    });
  });
  return out;
}

/**
 * The survey photographs as the Word file lays them: two across, each
 * 8.2 x 5.6 cm, the caption in its own row under each pair.
 */
export const PhotoPlateBlock: React.FC<PhotoPlateBlockProps> = ({
  block,
  assets = {},
  reportId,
  photoSlice,
  showHeading,
}) => {
  const lay = layoutOf(block);
  const label = block?.label || 'Survey Photographs';
  const photos = photoSlice || previewPhotos(block, assets, reportId);
  const heading = (
    <h2 className="text-[12px] font-bold text-[#00387A] uppercase tracking-wider border-b border-slate-300 pb-1 mb-2">
      {label}
    </h2>
  );

  if (!photos.length) {
    return (
      <div className="photo-plate-block my-2">
        {heading}
        <p className="text-xs italic text-slate-500 py-3">[No photos in this series]</p>
      </div>
    );
  }

  const edge = lay.border ? `1.5pt solid #${lay.border_color}` : 'none';
  // Cell padding in twips, as the tool sets it (see photo_layout.py).
  const tw = 2.54 / 1440;
  const pad = lay.border ? `${10 * tw}cm` : `${5 * tw}cm ${20 * tw}cm`;
  const rows: PreviewPhoto[][] = [];
  for (let i = 0; i < photos.length; i += 2) rows.push(photos.slice(i, i + 2));

  return (
    <div className="photo-plate-block">
      {(showHeading ?? lay.show_heading) && heading}
      <table className="mx-auto" style={{ borderCollapse: 'collapse' }}>
        <tbody>
          {rows.map((pair, r) => (
            <React.Fragment key={r}>
              <tr>
                {[0, 1].map((j) => {
                  const p = pair[j];
                  return (
                    <td key={j} style={{ padding: pad, border: p ? edge : 'none', verticalAlign: 'middle' }}>
                      {p ? (
                        p.imagePath ? (
                          <img
                            src={p.imagePath}
                            alt={p.caption}
                            style={{ width: `${PHOTO_W_CM}cm`, height: `${PHOTO_H_CM}cm`, display: 'block', objectFit: 'fill' }}
                          />
                        ) : (
                          <div
                            className="flex flex-col items-center justify-center text-slate-400 bg-slate-100"
                            style={{ width: `${PHOTO_W_CM}cm`, height: `${PHOTO_H_CM}cm` }}
                          >
                            <Camera className="w-8 h-8 stroke-[1.5]" />
                          </div>
                        )
                      ) : (
                        <div style={{ width: `${PHOTO_W_CM}cm` }} />
                      )}
                    </td>
                  );
                })}
              </tr>
              <tr>
                {[0, 1].map((j) => {
                  const p = pair[j];
                  return (
                    <td
                      key={j}
                      className="text-center photo-caption"
                      style={{
                        padding: `${5 * tw}cm ${20 * tw}cm`,
                        border: p ? edge : 'none',
                        fontFamily: `'${lay.caption_font}', sans-serif`,
                        fontSize: `${lay.caption_size}pt`,
                        color: `#${lay.caption_color}`,
                        lineHeight: 1.15,
                      }}
                    >
                      {p?.caption || ''}
                    </td>
                  );
                })}
              </tr>
            </React.Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
};

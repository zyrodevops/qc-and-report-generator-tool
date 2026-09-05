import React from 'react';
import { Camera } from 'lucide-react';

export interface PhotoPlateBlockProps {
  block: any;
  computed?: any;
  assets?: Record<string, any>;
  reportId?: string;
  photoSlice?: Array<{
    number: number;
    caption: string;
    assetId?: string;
    imagePath?: string;
  }>;
}

export const PhotoPlateBlock: React.FC<PhotoPlateBlockProps> = ({
  block,
  computed,
  assets = {},
  reportId,
  photoSlice,
}) => {
  const label = block?.label || 'Survey Photographs';
  const groups: any[] = block?.groups || [];
  const computedGroups = computed?.groups || {};

  // Build full photo list if not sliced externally
  let photos = photoSlice;
  if (!photos) {
    const all: Array<{
      number: number;
      caption: string;
      assetId?: string;
      imagePath?: string;
    }> = [];

    groups.forEach((g) => {
      const gid = g.id || '';
      const obs = g.observation || '';
      const assetIds: string[] = g.asset_ids || [];
      const grpComputed = computedGroups[gid] || {};
      const numbers: number[] =
        grpComputed.numbers || assetIds.map((_, i) => i + 1);

      assetIds.forEach((aid, idx) => {
        const num = numbers[idx] || idx + 1;
        const asset = assets[aid] || {};
        const derived = asset.derived_paths || asset.derived || {};
        const repId = reportId || block?.report_id || block?.reportId;
        const imgPath =
          asset.url ||
          (aid && repId ? `/api/reports/${repId}/assets/${aid}/image` : '') ||
          (typeof derived.display === 'string' && derived.display.startsWith('/api') ? derived.display : '') ||
          (typeof asset.original_path === 'string' && asset.original_path.startsWith('/api') ? asset.original_path : '');

        all.push({
          number: num,
          caption: `Photo No. ${num} \u2014 ${obs}`,
          assetId: aid,
          imagePath: imgPath,
        });
      });
    });

    photos = all;
  }

  if (!photos || photos.length === 0) {
    return (
      <div className="photo-plate-block my-2">
        <h2 className="text-[12px] font-bold text-[#00387A] uppercase tracking-wider border-b border-slate-300 pb-1 mb-2">
          {label}
        </h2>
        <p className="text-xs italic text-slate-500 py-3">[No photos in this series]</p>
      </div>
    );
  }

  return (
    <div className="photo-plate-block my-2">
      <h2 className="text-[12px] font-bold text-[#00387A] uppercase tracking-wider border-b border-slate-300 pb-1 mb-2">
        {label}
      </h2>
      <div className="grid grid-cols-2 gap-4 my-2">
        {photos.map((p, idx) => (
          <div
            key={idx}
            className="photo-card border border-slate-300 rounded bg-white p-2 flex flex-col items-center shadow-2xs"
          >
            <div className="aspect-[4/3] w-full bg-slate-100 rounded overflow-hidden flex items-center justify-center border border-slate-200">
              {p.imagePath ? (
                <img
                  src={p.imagePath}
                  alt={p.caption}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="flex flex-col items-center text-slate-400 gap-1 p-4 text-center">
                  <Camera className="w-8 h-8 stroke-[1.5]" />
                  <span className="text-[10px] font-mono">Photo No. {p.number}</span>
                </div>
              )}
            </div>
            <p className="photo-caption text-center text-[11px] font-medium text-slate-700 italic mt-2">
              {p.caption}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};

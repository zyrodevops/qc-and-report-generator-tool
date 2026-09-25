import React, { useState, useMemo } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  Camera,
  Upload,
  Trash2,
  ChevronLeft,
  ChevronRight,
  Maximize2,
  X,
  Sparkles,
  Download,
  Loader2,
  Check,
  Layers,
  Zap,
  RotateCcw,
  RotateCw,
} from 'lucide-react';
import { getAuthHeaders, rotatePhoto } from '../../api/client';
import { generateNormalModeDocx } from '../../utils/docxGenerator';
import { ImageData, ProModeOptions } from '../../types/photoStudio';
import BulkMode from './studio/BulkMode';
import ProMode from './studio/ProMode';
import { layoutOf, photoCaption, photoUrl, PhotoLayout, stripNumber } from '../../utils/photoLayout';
import { PhotoLayoutPanel } from './PhotoLayoutPanel';

interface PhotoGroup {
  id: string;
  observation: string;
  asset_ids: string[];
}

interface PhotoPlateBlockProps {
  block: {
    id: string;
    label?: string;
    series_id?: string;
    provenance?: string;
    groups: PhotoGroup[];
    /** How the photos are laid out in the report; see utils/photoLayout.ts. */
    layout?: Partial<PhotoLayout>;
  };
  reportId?: string;
  assets?: Record<string, any>;
  onChange: (updatedBlock: any) => void;
  onUpdateBlockAndAssets?: (updatedBlock: any, updatedAssets: Record<string, any>) => void;
}

// ── Caption Presets ─────────────────────────────────────────────────────────
const COMMON_PRESETS = [
  'Container exterior & seal intact',
  'Container right door opened',
  'Cargo stowage inside container',
  'Internal pulp temperature reading',
  'Sampled cartons opened for inspection',
  'Sound produce inspection',
  'Defect / decay fruit observed',
  'Packaging & labeling details',
];

// ── Tab Types ───────────────────────────────────────────────────────────────
type PhotoTab = 'manage' | 'bulk' | 'pro';

const TABS: { id: PhotoTab; label: string; icon: React.ReactNode; description: string }[] = [
  {
    id: 'manage',
    label: 'Upload & Manage',
    icon: <Camera className="w-4 h-4" />,
    description: 'Add photos, write captions, reorder',
  },
  {
    id: 'bulk',
    label: 'Bulk Upload',
    icon: <Layers className="w-4 h-4" />,
    description: 'Batch drag-drop queue, drag to reorder',
  },
  {
    id: 'pro',
    label: 'Pro Studio',
    icon: <Zap className="w-4 h-4" />,
    description: 'Custom fonts, borders, compression preset',
  },
];

// ────────────────────────────────────────────────────────────────────────────

export const PhotoTray: React.FC<PhotoPlateBlockProps> = ({
  block,
  reportId,
  assets = {},
  onChange,
  onUpdateBlockAndAssets,
}) => {
  const { groups = [], label = 'Survey Photographs' } = block;

  const [activeTab, setActiveTab] = useState<PhotoTab>('manage');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState('');
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);
  const [exportingDocx, setExportingDocx] = useState(false);

  const [turning, setTurning] = useState<string | null>(null);

  // Numbers and caption wording come from the photo section's layout; they
  // are worked out, never typed into the caption text.
  const layout = layoutOf(block);
  const setLayout = (next: PhotoLayout) => onChange({ ...block, layout: next });

  // Flatten groups into a clean ordered list of photos (computed fresh per Rule #1)
  const flatPhotos = useMemo(() => {
    let currentNum = layout.number_from;
    const list: Array<{
      aid: string;
      groupId: string;
      photoNumber: number;
      observation: string;
      url: string;
      exifDate?: string;
    }> = [];

    groups.forEach((g) => {
      (g.asset_ids || []).forEach((aid) => {
        const asset = assets[aid] || {};
        const exif = asset.exif || {};
        const exifDate = exif.DateTimeOriginal || exif.DateTime || '';
        list.push({
          aid,
          groupId: g.id,
          photoNumber: currentNum++,
          observation: g.observation || '',
          url: photoUrl(reportId, aid, asset),
          exifDate: exifDate ? String(exifDate) : undefined,
        });
      });
    });
    return list;
  }, [groups, assets, reportId, layout.number_from]);

  // Reconstruct block groups from flat list
  const syncPhotosToBlock = (
    newPhotos: Array<{ aid: string; groupId: string; observation: string }>,
    customAssets?: Record<string, any>
  ) => {
    const updatedGroups: PhotoGroup[] = newPhotos.map((p) => ({
      id: p.groupId || `pg_${p.aid}`,
      observation: p.observation,
      asset_ids: [p.aid],
    }));

    const updatedBlock = {
      ...block,
      groups: updatedGroups,
    };

    if (onUpdateBlockAndAssets) {
      onUpdateBlockAndAssets(updatedBlock, customAssets || assets);
    } else {
      onChange(updatedBlock);
    }
  };

  // Batch upload photos
  const handleBatchUpload = async (files: File[]) => {
    if (!files || files.length === 0) return;
    if (!reportId) {
      alert('Report ID is missing. Please save report draft first.');
      return;
    }

    setUploading(true);
    setUploadProgress(`Uploading and hashing ${files.length} photo${files.length > 1 ? 's' : ''}...`);

    try {
      const formData = new FormData();
      files.forEach((f) => formData.append('files', f));
      formData.append('series_id', block.series_id || 'survey');
      formData.append('provenance', block.provenance || 'own_survey');
      formData.append('landscape', layout.landscape ? 'true' : 'false');

      const headers = getAuthHeaders();
      const res = await fetch(`/api/reports/${reportId}/assets/photos/batch`, {
        method: 'POST',
        headers,
        body: formData,
      });

      if (!res.ok) {
        const errText = await res.text();
        let msg = `Batch upload failed (HTTP ${res.status})`;
        try {
          const errJson = JSON.parse(errText);
          msg = errJson.detail || errJson.message || msg;
        } catch {
          if (errText) msg += `: ${errText}`;
        }
        throw new Error(msg);
      }

      const data = await res.json();
      const uploadedAssets: any[] = data.assets || [];

      if (uploadedAssets.length > 0) {
        const nextAssets = { ...assets };
        uploadedAssets.forEach((a) => {
          nextAssets[a.id] = a;
        });

        const newPhotoEntries = uploadedAssets.map((a) => ({
          aid: a.id,
          groupId: `pg_${a.id}`,
          observation: '',
        }));

        const existingEntries = flatPhotos.map((p) => ({
          aid: p.aid,
          groupId: p.groupId,
          observation: p.observation,
        }));

        syncPhotosToBlock([...existingEntries, ...newPhotoEntries], nextAssets);
      }
    } catch (err: any) {
      console.error('Photo upload error:', err);
      alert(err.message || 'Failed to upload photos.');
    } finally {
      setUploading(false);
      setUploadProgress('');
    }
  };

  // Dropzone
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: handleBatchUpload,
    accept: {
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
      'image/bmp': ['.bmp'],
      'image/webp': ['.webp'],
    },
    disabled: uploading || !reportId,
    multiple: true,
  });

  const handleUpdateCaption = (index: number, caption: string) => {
    const next = flatPhotos.map((p, idx) => ({
      aid: p.aid,
      groupId: p.groupId,
      observation: idx === index ? caption : p.observation,
    }));
    syncPhotosToBlock(next);
  };

  const handleApplyPreset = (index: number, preset: string) => {
    const current = flatPhotos[index]?.observation || '';
    const newCaption = current ? `${current} • ${preset}` : preset;
    handleUpdateCaption(index, newCaption);
  };

  const handleMovePhoto = (index: number, direction: 'left' | 'right') => {
    const target = direction === 'left' ? index - 1 : index + 1;
    if (target < 0 || target >= flatPhotos.length) return;

    const list = [...flatPhotos];
    const temp = list[index];
    list[index] = list[target];
    list[target] = temp;
    syncPhotosToBlock(list.map((p) => ({ aid: p.aid, groupId: p.groupId, observation: p.observation })));
  };

  const handleDeletePhoto = (index: number) => {
    const remaining = flatPhotos.filter((_, idx) => idx !== index);
    syncPhotosToBlock(remaining.map((p) => ({ aid: p.aid, groupId: p.groupId, observation: p.observation })));

    if (lightboxIndex !== null) {
      setLightboxIndex(null);
    }
  };

  // A quarter turn, made on the server from the original (which is never changed).
  const handleRotate = async (aid: string, turns: 1 | -1) => {
    if (!reportId) return;
    setTurning(aid);
    try {
      const entry = await rotatePhoto(reportId, aid, turns);
      const nextAssets = { ...assets, [aid]: { ...(assets[aid] || {}), ...entry } };
      if (onUpdateBlockAndAssets) onUpdateBlockAndAssets(block, nextAssets);
    } catch (err: any) {
      alert(err.message || 'Could not turn the photo.');
    } finally {
      setTurning(null);
    }
  };

  const handleExportDocx = async () => {
    if (flatPhotos.length === 0) {
      alert('No photos available to export.');
      return;
    }
    setExportingDocx(true);
    try {
      const imageDataList: ImageData[] = await Promise.all(
        flatPhotos.map(async (p) => {
          const res = await fetch(p.url);
          const blob = await res.blob();
          return {
            id: p.aid,
            file: new File([blob], `photo_${p.photoNumber}.jpg`, { type: blob.type }),
            preview: p.url,
            description: photoCaption(layout, p.photoNumber, p.observation),
            processedBlob: blob,
          };
        })
      );
      await generateNormalModeDocx(imageDataList, `${label.replace(/\s+/g, '_')}_Annexure`);
    } catch (err: any) {
      console.error('Docx export failed:', err);
      alert('Failed to generate standalone Word annexure.');
    } finally {
      setExportingDocx(false);
    }
  };

  // Called from Bulk/Pro modes to send photos to this report block
  const handleSendToReport = async (photos: ImageData[], options?: ProModeOptions) => {
    if (!reportId) {
      alert('No active report selected.');
      return;
    }

    const formData = new FormData();
    photos.forEach((p) => {
      formData.append('files', p.processedBlob ? new File([p.processedBlob], p.file.name, { type: 'image/jpeg' }) : p.file);
    });
    formData.append('series_id', block?.series_id || 'survey');
    formData.append('provenance', block?.provenance || 'own_survey');

    const headers = getAuthHeaders();
    const res = await fetch(`/api/reports/${reportId}/assets/photos/batch`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!res.ok) {
      const errText = await res.text();
      let msg = `Batch upload failed (HTTP ${res.status})`;
      try {
        const errJson = JSON.parse(errText);
        msg = errJson.detail || msg;
      } catch {
        if (errText) msg += `: ${errText}`;
      }
      throw new Error(msg);
    }

    const data = await res.json();
    const uploadedAssets: any[] = data.assets || [];

    const nextAssets = { ...assets };
    uploadedAssets.forEach((a: any) => {
      nextAssets[a.id] = a;
    });

    // Each photo gets its own group with its description as the observation;
    // a number the studio typed into it is dropped, the report numbers them.
    const newEntries = uploadedAssets.map((a: any, i: number) => ({
      aid: a.id,
      groupId: `pg_${a.id}`,
      observation: stripNumber(photos[i]?.description || ''),
    }));

    const existingEntries = flatPhotos.map((p) => ({
      aid: p.aid,
      groupId: p.groupId,
      observation: p.observation,
    }));

    if (options) {
      // Pro Studio's choices carry over to how the report prints the photos.
      const kw = options.isCustomKeyword ? options.customKeyword || layout.caption_keyword : options.autoNumberKeyword;
      block = {
        ...block,
        layout: {
          ...layout,
          border: options.addBorder,
          border_color: options.boxColor,
          caption_keyword: kw,
          number_from: options.useCustomNumberStart ? options.numberStartFrom || 1 : layout.number_from,
          caption_font: options.fontType,
          caption_size: options.fontSize,
          caption_color: options.fontColor,
          quality: options.compressionEnabled ? options.compressionPreset : 'original',
        },
      };
    }
    syncPhotosToBlock([...existingEntries, ...newEntries], nextAssets);

    // Switch back to manage tab to see the uploaded photos
    setActiveTab('manage');
  };

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="bg-white rounded-3xl shadow-xs border border-gray-200 overflow-hidden">
      {/* ── Block Header ──────────────────────────────────────────────────── */}
      <div className="px-6 py-4 bg-slate-900 text-white flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-600 rounded-xl">
            <Camera className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-base tracking-tight">{label}</h3>
              <span className="text-xs bg-indigo-500/30 text-indigo-200 font-semibold px-2.5 py-0.5 rounded-full border border-indigo-400/30">
                {flatPhotos.length} Photo{flatPhotos.length === 1 ? '' : 's'}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              {layout.per_page} to a page · Numbered in the report · Originals kept unchanged
            </p>
          </div>
        </div>

        {/* Quick actions */}
        <div className="flex items-center gap-2">
          {flatPhotos.length > 0 && (
            <button
              type="button"
              onClick={handleExportDocx}
              disabled={exportingDocx}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white border border-slate-600 rounded-xl text-xs font-semibold transition disabled:opacity-50 cursor-pointer"
              title="Download standalone 2-column Word annexure DOCX"
            >
              {exportingDocx ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
              <span>Export DOCX</span>
            </button>
          )}
          <div {...getRootProps()}>
            <input {...getInputProps()} />
            <button
              type="button"
              disabled={uploading || !reportId}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold shadow-xs transition disabled:opacity-50 cursor-pointer"
            >
              <Upload className="w-3.5 h-3.5" />
              <span>Add Photos</span>
            </button>
          </div>
        </div>
      </div>

      {/* ── Tab Bar ───────────────────────────────────────────────────────── */}
      <div className="border-b border-gray-200 bg-gray-50 px-6 flex gap-1 pt-2">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-t-xl border-b-2 transition cursor-pointer ${
              activeTab === tab.id
                ? 'border-indigo-600 text-indigo-700 bg-white shadow-xs'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-100'
            }`}
            title={tab.description}
          >
            {tab.icon}
            <span>{tab.label}</span>
            {tab.id === 'manage' && flatPhotos.length > 0 && (
              <span className="ml-0.5 bg-indigo-100 text-indigo-700 text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                {flatPhotos.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ── Tab Content ───────────────────────────────────────────────────── */}
      <div className="p-6">

        {/* ────── MANAGE TAB ────── */}
        {activeTab === 'manage' && (
          <div className="space-y-5">

            {/* Upload progress banner */}
            {uploading && (
              <div className="p-4 bg-indigo-50 border border-indigo-200 rounded-2xl flex items-center gap-3 text-indigo-800 text-xs font-medium animate-pulse">
                <Loader2 className="w-4 h-4 text-indigo-600 animate-spin shrink-0" />
                <span>{uploadProgress || 'Uploading and hashing photos...'}</span>
              </div>
            )}

            {/* Empty state drop zone */}
            {flatPhotos.length === 0 ? (
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-3xl p-12 text-center transition-all cursor-pointer flex flex-col items-center justify-center ${
                  isDragActive
                    ? 'border-indigo-500 bg-indigo-50/50 scale-[1.01]'
                    : 'border-gray-300 hover:border-indigo-400 hover:bg-slate-50/70 bg-white'
                }`}
              >
                <input {...getInputProps()} />
                <div className="w-16 h-16 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center mb-4 shadow-xs">
                  <Upload className="w-8 h-8" />
                </div>
                <h4 className="text-base font-bold text-gray-800">
                  {isDragActive ? 'Drop survey photographs here...' : 'Upload Survey Photographs'}
                </h4>
                <p className="text-xs text-gray-500 mt-1.5 max-w-md">
                  Drag and drop multiple photos here, or click to browse. Bit-exact originals stored with SHA-256.
                </p>
                <div className="mt-4 text-xs text-gray-400">
                  or use the <strong className="text-indigo-600">Bulk Upload</strong> tab for drag-to-reorder queue,
                  or <strong className="text-indigo-600">Pro Studio</strong> for custom DOCX formatting
                </div>
              </div>
            ) : (
              <>
                {/* Compact secondary drop zone */}
                <div
                  {...getRootProps()}
                  className={`border border-dashed rounded-2xl p-3 text-center transition-all cursor-pointer flex items-center justify-center gap-2 text-xs ${
                    isDragActive
                      ? 'border-indigo-500 bg-indigo-50/60 text-indigo-800 font-semibold'
                      : 'border-gray-200 bg-gray-50/60 hover:bg-indigo-50/30 text-gray-400 hover:text-indigo-600'
                  }`}
                >
                  <input {...getInputProps()} />
                  <Upload className="w-3.5 h-3.5" />
                  <span>{isDragActive ? 'Drop photos now...' : 'Drag more photos here, or click to browse'}</span>
                </div>

                {/* ── How the photos look in the report (the photo tool's options) ── */}
                <PhotoLayoutPanel layout={layout} onChange={setLayout} />

                {/* ── 2-Column Photo Grid ── */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  {flatPhotos.map((photo, index) => (
                    <div
                      key={photo.aid}
                      className="bg-white border border-gray-200 rounded-2xl overflow-hidden shadow-xs hover:shadow-md hover:border-gray-300 transition-all flex flex-col"
                    >
                      {/* Card header */}
                      <div className="px-4 py-2.5 bg-slate-50 border-b border-gray-100 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold bg-indigo-600 text-white px-2 py-0.5 rounded-lg shadow-xs">
                            {layout.caption_keyword} {photo.photoNumber}
                          </span>
                          {photo.exifDate && (
                            <span className="text-[10px] text-gray-400 font-mono">{photo.exifDate}</span>
                          )}
                        </div>
                        <div className="flex items-center gap-1">
                          <button
                            type="button"
                            onClick={() => handleRotate(photo.aid, 1)}
                            disabled={turning !== null}
                            className="p-1 rounded text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 disabled:opacity-30 transition cursor-pointer"
                            title="Turn left"
                            aria-label={`Turn photo ${photo.photoNumber} left`}
                          >
                            {turning === photo.aid ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />}
                          </button>
                          <button
                            type="button"
                            onClick={() => handleRotate(photo.aid, -1)}
                            disabled={turning !== null}
                            className="p-1 rounded text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 disabled:opacity-30 transition cursor-pointer mr-1"
                            title="Turn right"
                            aria-label={`Turn photo ${photo.photoNumber} right`}
                          >
                            <RotateCw className="w-4 h-4" />
                          </button>
                          <button
                            type="button"
                            onClick={() => handleMovePhoto(index, 'left')}
                            disabled={index === 0}
                            className="p-1 rounded text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 disabled:opacity-20 transition cursor-pointer"
                            title="Move earlier"
                          >
                            <ChevronLeft className="w-4 h-4" />
                          </button>
                          <button
                            type="button"
                            onClick={() => handleMovePhoto(index, 'right')}
                            disabled={index === flatPhotos.length - 1}
                            className="p-1 rounded text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 disabled:opacity-20 transition cursor-pointer"
                            title="Move later"
                          >
                            <ChevronRight className="w-4 h-4" />
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDeletePhoto(index)}
                            className="p-1 rounded text-gray-400 hover:text-red-600 hover:bg-red-50 transition ml-1 cursor-pointer"
                            title="Delete photo"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>

                      {/* Image */}
                      <div className="relative group bg-slate-900 aspect-video flex items-center justify-center overflow-hidden">
                        <img
                          src={photo.url}
                          alt={`Photo ${photo.photoNumber}`}
                          className="w-full h-full object-contain transition-transform duration-200 group-hover:scale-[1.02]"
                          onError={(e) => { e.currentTarget.style.display = 'none'; }}
                        />
                        <button
                          type="button"
                          onClick={() => setLightboxIndex(index)}
                          className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-white gap-2 cursor-pointer"
                        >
                          <div className="p-2 bg-black/60 rounded-xl backdrop-blur-xs flex items-center gap-1.5 text-xs font-semibold">
                            <Maximize2 className="w-4 h-4" />
                            <span>View Full Size</span>
                          </div>
                        </button>
                      </div>

                      {/* Caption */}
                      <div className="p-4 space-y-2 bg-white flex-1 flex flex-col justify-between">
                        <div>
                          <label className="block text-[11px] font-bold uppercase tracking-wider text-gray-500 mb-1">
                            Text after the number (optional)
                          </label>
                          <input
                            type="text"
                            value={photo.observation}
                            onChange={(e) => handleUpdateCaption(index, e.target.value)}
                            placeholder={`Prints as "${photoCaption(layout, photo.photoNumber)}"`}
                            className="w-full px-3 py-2 bg-slate-50 border border-gray-200 rounded-xl text-xs text-gray-800 focus:bg-white focus:ring-2 focus:ring-indigo-500 focus:outline-hidden transition"
                          />
                        </div>
                        {/* Preset chips */}
                        <div className="flex flex-wrap gap-1.5 pt-1">
                          {COMMON_PRESETS.slice(0, 4).map((preset) => (
                            <button
                              key={preset}
                              type="button"
                              onClick={() => handleApplyPreset(index, preset)}
                              className="text-[10px] bg-gray-100 hover:bg-indigo-50 hover:text-indigo-700 text-gray-600 px-2 py-0.5 rounded-lg border border-gray-200 hover:border-indigo-200 transition cursor-pointer"
                            >
                              + {preset}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        {/* ────── BULK UPLOAD TAB ────── */}
        {activeTab === 'bulk' && (
          <div className="space-y-4">
            <div className="flex items-start gap-3 p-4 bg-blue-50 border border-blue-200 rounded-2xl text-xs text-blue-800">
              <Layers className="w-4 h-4 shrink-0 mt-0.5 text-blue-600" />
              <div>
                <strong>Bulk Upload Mode</strong> — Drag and drop any number of photos into the queue below.
                Drag cards to reorder. Add captions per photo. Click <strong>Send to Report</strong> to add them all to this block.
              </div>
            </div>
            <div className="bg-gray-50 rounded-2xl border border-gray-200 p-1">
              <BulkMode
                onSendToReport={reportId ? handleSendToReport : undefined}
                reportId={reportId}
              />
            </div>
          </div>
        )}

        {/* ────── PRO STUDIO TAB ────── */}
        {activeTab === 'pro' && (
          <div className="space-y-4">
            <div className="flex items-start gap-3 p-4 bg-amber-50 border border-amber-200 rounded-2xl text-xs text-amber-800">
              <Zap className="w-4 h-4 shrink-0 mt-0.5 text-amber-600" />
              <div>
                <strong>Pro Studio Mode</strong> — Customize font, borders, compression quality, and auto-numbering
                keyword. <strong>Download DOCX</strong> generates a standalone Word photo annexure.
                <strong>Send to Report</strong> adds photos to this block.
              </div>
            </div>
            <div className="bg-gray-50 rounded-2xl border border-gray-200 p-1">
              <ProMode
                onSendToReport={reportId ? handleSendToReport : undefined}
                reportId={reportId}
              />
            </div>
          </div>
        )}
      </div>

      {/* ── Lightbox ──────────────────────────────────────────────────────── */}
      {lightboxIndex !== null && flatPhotos[lightboxIndex] && (
        <div className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex flex-col items-center justify-between p-4 sm:p-6 animate-in fade-in duration-150">
          <div className="w-full max-w-5xl flex items-center justify-between text-white pb-3 border-b border-gray-800">
            <div className="flex items-center gap-3">
              <span className="font-mono text-sm font-bold bg-indigo-600 px-3 py-1 rounded-lg">
                Photo {flatPhotos[lightboxIndex].photoNumber} of {flatPhotos.length}
              </span>
              <span className="text-xs text-gray-300">
                {flatPhotos[lightboxIndex].observation || 'No observation caption'}
              </span>
            </div>
            <button
              type="button"
              onClick={() => setLightboxIndex(null)}
              className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-xl transition cursor-pointer"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          <div className="flex-1 w-full max-w-5xl flex items-center justify-center p-4 relative">
            <img
              src={flatPhotos[lightboxIndex].url}
              alt={`Photo ${flatPhotos[lightboxIndex].photoNumber}`}
              className="max-h-[78vh] max-w-full object-contain rounded-xl shadow-2xl"
            />
            {lightboxIndex > 0 && (
              <button
                type="button"
                onClick={() => setLightboxIndex(lightboxIndex - 1)}
                className="absolute left-2 p-3 bg-black/60 hover:bg-indigo-600 text-white rounded-full backdrop-blur-xs transition cursor-pointer"
              >
                <ChevronLeft className="w-6 h-6" />
              </button>
            )}
            {lightboxIndex < flatPhotos.length - 1 && (
              <button
                type="button"
                onClick={() => setLightboxIndex(lightboxIndex + 1)}
                className="absolute right-2 p-3 bg-black/60 hover:bg-indigo-600 text-white rounded-full backdrop-blur-xs transition cursor-pointer"
              >
                <ChevronRight className="w-6 h-6" />
              </button>
            )}
          </div>

          <div className="w-full max-w-3xl text-center text-xs text-gray-400 pb-2">
            Use arrow buttons or keyboard to navigate • Esc or click × to close
          </div>
        </div>
      )}
    </div>
  );
};

export default PhotoTray;

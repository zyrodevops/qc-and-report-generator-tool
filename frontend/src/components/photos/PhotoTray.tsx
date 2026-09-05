import React, { useState } from 'react';
import { Camera, Plus, Trash2, ExternalLink, Image as ImageIcon, ChevronUp, ChevronDown } from 'lucide-react';
import { getAuthHeaders } from '../../api/client';

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
  };
  reportId?: string;
  assets?: Record<string, any>;
  onChange: (updatedBlock: any) => void;
  onUpdateBlockAndAssets?: (updatedBlock: any, updatedAssets: Record<string, any>) => void;
}

export const PhotoTray: React.FC<PhotoPlateBlockProps> = ({
  block,
  reportId,
  assets = {},
  onChange,
  onUpdateBlockAndAssets,
}) => {
  const { groups = [], label = 'Survey Photographs' } = block;
  const [uploading, setUploading] = useState(false);
  const [newObs, setNewObs] = useState('');

  // Client's existing external bulk photo tool
  const EXTERNAL_BULK_UPLOADER = 'https://httpsmarinecargo-autoonrender.com/';

  // Re-compute photo ranges for display
  let currentNum = 1;
  const groupRanges = groups.map((g) => {
    const count = g.asset_ids.length;
    if (count === 0) {
      return { ...g, start: currentNum, end: currentNum, count: 0, label: '(No photos)' };
    }
    const start = currentNum;
    const end = currentNum + count - 1;
    currentNum += count;

    let rangeLabel = '';
    if (count === 1) {
      rangeLabel = `(Photo No. ${start})`;
    } else if (count === 2) {
      rangeLabel = `(Photo Nos. ${start} & ${end})`;
    } else {
      rangeLabel = `(Photo Nos. ${start} to ${end})`;
    }

    return { ...g, start, end, count, label: rangeLabel };
  });

  const handleAddGroup = () => {
    if (!newObs.trim()) return;
    const newGroup: PhotoGroup = {
      id: `pg_${Date.now()}`,
      observation: newObs.trim(),
      asset_ids: [],
    };
    onChange({
      ...block,
      groups: [...groups, newGroup],
    });
    setNewObs('');
  };

  const handleDeleteGroup = (idx: number) => {
    const updated = groups.filter((_, i) => i !== idx);
    onChange({ ...block, groups: updated });
  };

  const handleMoveGroup = (idx: number, direction: 'up' | 'down') => {
    const targetIdx = direction === 'up' ? idx - 1 : idx + 1;
    if (targetIdx < 0 || targetIdx >= groups.length) return;
    const updated = [...groups];
    const temp = updated[idx];
    updated[idx] = updated[targetIdx];
    updated[targetIdx] = temp;
    onChange({ ...block, groups: updated });
  };

  const handleUpdateObservation = (idx: number, text: string) => {
    const updated = [...groups];
    updated[idx] = { ...updated[idx], observation: text };
    onChange({ ...block, groups: updated });
  };

  const handlePhotoUpload = async (groupIdx: number, files: FileList | null) => {
    if (!files || files.length === 0) return;
    if (!reportId) {
      alert('Report ID is missing. Please save draft first.');
      return;
    }
    setUploading(true);

    try {
      const uploadedIds: string[] = [];
      const uploadedAssets: any[] = [];
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const formData = new FormData();
        formData.append('file', file);
        formData.append('series_id', block.series_id || 'survey');
        formData.append('provenance', block.provenance || 'own_survey');

        const headers = getAuthHeaders();
        const res = await fetch(`/api/reports/${reportId}/assets/photos`, {
          method: 'POST',
          headers,
          body: formData,
        });

        if (res.ok) {
          const data = await res.json();
          uploadedIds.push(data.id);
          uploadedAssets.push(data);
        } else {
          const errText = await res.text();
          let msg = `Upload failed (HTTP ${res.status})`;
          try {
            const errJson = JSON.parse(errText);
            msg = errJson.detail || errJson.message || msg;
          } catch {
            if (errText) msg += `: ${errText}`;
          }
          alert(msg);
        }
      }

      if (uploadedIds.length > 0) {
        const updated = [...groups];
        updated[groupIdx] = {
          ...updated[groupIdx],
          asset_ids: [...updated[groupIdx].asset_ids, ...uploadedIds],
        };

        const nextAssets = { ...(assets || {}) };
        uploadedAssets.forEach((a) => {
          nextAssets[a.id] = a;
        });

        if (onUpdateBlockAndAssets) {
          onUpdateBlockAndAssets({ ...block, groups: updated }, nextAssets);
        } else {
          onChange({ ...block, groups: updated });
        }
      }
    } catch (err: any) {
      console.error('Failed to upload photos:', err);
      alert(`Upload error: ${err?.message || err}`);
    } finally {
      setUploading(false);
    }
  };

  const handleRemovePhoto = (groupIdx: number, photoId: string) => {
    const updated = [...groups];
    updated[groupIdx] = {
      ...updated[groupIdx],
      asset_ids: updated[groupIdx].asset_ids.filter((id) => id !== photoId),
    };
    onChange({ ...block, groups: updated });
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-5">
      <div className="flex flex-wrap justify-between items-center gap-3 pb-3 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <Camera className="w-5 h-5 text-indigo-600" />
          <h3 className="font-bold text-gray-800 text-lg">{label}</h3>
          <span className="text-xs bg-indigo-50 text-indigo-700 font-semibold px-2 py-0.5 rounded border border-indigo-200">
            Total Photos: {currentNum - 1}
          </span>
        </div>

        <a
          href={EXTERNAL_BULK_UPLOADER}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-1.5 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold px-3 py-1.5 rounded transition border border-gray-300"
          title="Open Marine Cargo Agencies bulk photo tool (Passcode: 1234)"
        >
          <ExternalLink className="w-3.5 h-3.5 text-indigo-600" />
          Open External Bulk Uploader Tool
        </a>
      </div>

      {/* Observation groups list */}
      <div className="space-y-4">
        {groupRanges.map((g, idx) => (
          <div
            key={g.id}
            className="border border-gray-200 rounded-lg p-4 bg-gray-50/50 hover:bg-gray-50 transition space-y-3"
          >
            <div className="flex justify-between items-start gap-3">
              <div className="flex-1 space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm font-bold text-indigo-700 bg-indigo-100/70 px-2 py-0.5 rounded">
                    {g.label}
                  </span>
                  <span className="text-xs text-gray-500">
                    ({g.asset_ids.length} photo{g.asset_ids.length === 1 ? '' : 's'})
                  </span>
                </div>
                <input
                  type="text"
                  value={g.observation}
                  onChange={(e) => handleUpdateObservation(idx, e.target.value)}
                  placeholder="Observation caption for this photo group..."
                  className="w-full px-3 py-1.5 bg-white border border-gray-300 rounded text-sm text-gray-800 focus:ring-1 focus:ring-indigo-500 outline-none"
                />
              </div>

              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => handleMoveGroup(idx, 'up')}
                  disabled={idx === 0}
                  className="text-gray-400 hover:text-indigo-600 disabled:opacity-30 disabled:hover:text-gray-400 p-1 transition"
                  title="Move group up (renumbers automatically)"
                >
                  <ChevronUp className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={() => handleMoveGroup(idx, 'down')}
                  disabled={idx === groups.length - 1}
                  className="text-gray-400 hover:text-indigo-600 disabled:opacity-30 disabled:hover:text-gray-400 p-1 transition"
                  title="Move group down (renumbers automatically)"
                >
                  <ChevronDown className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={() => handleDeleteGroup(idx)}
                  className="text-gray-400 hover:text-red-500 p-1 transition ml-1"
                  title="Remove group"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Photos in this group */}
            <div className="flex flex-wrap gap-2 items-center pt-2">
              {g.asset_ids.map((aid, pIdx) => (
                <div
                  key={aid}
                  className="relative group bg-white border border-gray-300 rounded p-1.5 flex items-center gap-2 shadow-xs hover:border-indigo-300 transition"
                >
                  <img
                    src={`/api/reports/${reportId}/assets/${aid}/image`}
                    alt={`Photo ${g.start + pIdx}`}
                    className="w-10 h-10 object-cover rounded border border-gray-200"
                    onError={(e) => {
                      e.currentTarget.style.display = 'none';
                    }}
                  />
                  <ImageIcon className="w-4 h-4 text-gray-400" />
                  <span className="text-xs font-mono font-medium text-gray-700">Photo {g.start + pIdx}</span>
                  <button
                    type="button"
                    onClick={() => handleRemovePhoto(idx, aid)}
                    className="text-gray-400 hover:text-red-500 p-0.5 transition ml-1"
                    title="Delete photo"
                  >
                    ×
                  </button>
                </div>
              ))}

              <label className="cursor-pointer inline-flex items-center gap-1 text-xs bg-white hover:bg-gray-100 text-gray-700 font-medium px-2.5 py-1.5 rounded border border-gray-300 border-dashed transition">
                <Plus className="w-3.5 h-3.5 text-indigo-600" />
                {uploading ? 'Uploading...' : 'Upload Photo(s)'}
                <input
                  type="file"
                  multiple
                  accept="image/*"
                  disabled={uploading || !reportId}
                  onChange={(e) => {
                    handlePhotoUpload(idx, e.target.files);
                    e.target.value = '';
                  }}
                  className="hidden"
                />
              </label>
            </div>
          </div>
        ))}

        {groups.length === 0 && (
          <p className="text-sm text-gray-500 italic py-3 text-center">
            No photo groups created yet. Add an observation group below to start organizing survey photos.
          </p>
        )}
      </div>

      {/* Add group input */}
      <div className="flex gap-2 pt-2 border-t border-gray-100">
        <input
          type="text"
          value={newObs}
          onChange={(e) => setNewObs(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleAddGroup()}
          placeholder="New photo group observation (e.g., 'Internal pulp temperature reading 1.2°C')..."
          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
        />
        <button
          type="button"
          onClick={handleAddGroup}
          className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition"
        >
          <Plus className="w-4 h-4" />
          Add Observation Group
        </button>
      </div>
    </div>
  );
};


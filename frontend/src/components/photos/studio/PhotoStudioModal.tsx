import React, { useState } from 'react';
import { X, Camera, ArrowLeft } from 'lucide-react';
import { Mode, ImageData } from '../../../types/photoStudio';
import ModeSelector from './ModeSelector';
import NormalMode from './NormalMode';
import BulkMode from './BulkMode';
import ProMode from './ProMode';
import { getAuthHeaders } from '../../../api/client';

interface PhotoStudioModalProps {
  isOpen: boolean;
  onClose: () => void;
  reportId?: string;
  block?: any;
  assets?: Record<string, any>;
  onUpdateBlockAndAssets?: (updatedBlock: any, updatedAssets: Record<string, any>) => void;
}

export const PhotoStudioModal: React.FC<PhotoStudioModalProps> = ({
  isOpen,
  onClose,
  reportId,
  block,
  assets = {},
  onUpdateBlockAndAssets,
}) => {
  const [selectedMode, setSelectedMode] = useState<Mode>('bulk');

  if (!isOpen) return null;

  const handleSendToReport = async (photos: ImageData[]) => {
    if (!reportId) {
      alert('No active report selected.');
      return;
    }

    const formData = new FormData();
    photos.forEach((p) => {
      formData.append('files', p.file);
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
    const uploadedAssets = data.assets || [];

    // Create a new observation group in the block for these photos,
    // or group them by descriptions
    const newGroup = {
      id: `pg_${Date.now()}`,
      observation: photos[0]?.description || 'Batch imported survey photos',
      asset_ids: uploadedAssets.map((a: any) => a.id),
    };

    const currentGroups = block?.groups ? [...block.groups] : [];
    const updatedBlock = {
      ...block,
      groups: [...currentGroups, newGroup],
    };

    const nextAssets = { ...assets };
    uploadedAssets.forEach((a: any) => {
      nextAssets[a.id] = a;
    });

    if (onUpdateBlockAndAssets) {
      onUpdateBlockAndAssets(updatedBlock, nextAssets);
    }

    alert(`Successfully imported ${uploadedAssets.length} photos into the report!`);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/70 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6">
      <div className="bg-white rounded-3xl max-w-6xl w-full max-h-[90vh] flex flex-col shadow-2xl border border-gray-200 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-900 text-white flex justify-between items-center border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-600 rounded-xl text-white shadow-xs">
              <Camera className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold tracking-tight">Photo Annexure Studio</h2>
                <span className="text-[11px] font-semibold bg-indigo-500/30 text-indigo-200 px-2 py-0.5 rounded-full border border-indigo-400/30">
                  Native Client Tool
                </span>
              </div>
              <p className="text-xs text-slate-400">
                {reportId
                  ? `Active Report Context: #${reportId}`
                  : 'Standalone Photo Sheet & Annexure Generator'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {selectedMode && (
              <button
                type="button"
                onClick={() => setSelectedMode(null)}
                className="flex items-center gap-1 text-xs text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded-lg transition"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Switch Mode</span>
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition"
              title="Close modal"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-50/50">
          {!selectedMode ? (
            <ModeSelector
              selectedMode={selectedMode}
              onModeSelect={(m) => setSelectedMode(m)}
            />
          ) : (
            <div className="bg-white rounded-2xl border border-gray-200 shadow-xs p-6">
              <div className="flex justify-between items-center mb-6 pb-4 border-b border-gray-100">
                <h3 className="text-lg font-bold text-gray-900">
                  {selectedMode === 'normal' && 'Normal Mode — Fixed-Count Upload Grid'}
                  {selectedMode === 'bulk' && 'Bulk Mode — Batch Drag & Drop Queue'}
                  {selectedMode === 'pro' && 'Pro Mode — Customized Word Annexure Studio'}
                </h3>
                <span className="text-xs font-semibold px-2.5 py-1 rounded bg-slate-100 text-slate-700">
                  {reportId ? 'Report Linked' : 'Standalone'}
                </span>
              </div>

              {selectedMode === 'normal' && (
                <NormalMode
                  onSendToReport={reportId ? handleSendToReport : undefined}
                  reportId={reportId}
                />
              )}
              {selectedMode === 'bulk' && (
                <BulkMode
                  onSendToReport={reportId ? handleSendToReport : undefined}
                  reportId={reportId}
                />
              )}
              {selectedMode === 'pro' && (
                <ProMode
                  onSendToReport={reportId ? handleSendToReport : undefined}
                  reportId={reportId}
                />
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-white border-t border-gray-200 text-xs text-gray-500 flex justify-between items-center">
          <span>Marine Cargo Agencies Private Limited • Bit-Exact Original Photo Storage Verified</span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold rounded-lg transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default PhotoStudioModal;

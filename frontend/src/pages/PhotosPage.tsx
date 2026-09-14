/**
 * PhotosPage — Standalone Photo Annexure Studio
 *
 * Accessible from the global header "📷 Photo Studio" button.
 * All three modes (Normal, Bulk, Pro) are tabs on a single page —
 * no modal required. Shows which report is currently active.
 */
import React, { useState } from 'react';
import { Camera, Layers, Zap, Grid, ArrowLeft, X } from 'lucide-react';
import { ImageData, Mode } from '../types/photoStudio';
import NormalMode from '../components/photos/studio/NormalMode';
import BulkMode from '../components/photos/studio/BulkMode';
import ProMode from '../components/photos/studio/ProMode';
import { getAuthHeaders } from '../api/client';

interface PhotosPageProps {
  reportId?: string;
  reportNumber?: string;
  onClose: () => void;
}

const MODES: {
  id: Exclude<Mode, null>;
  label: string;
  shortLabel: string;
  icon: React.ReactNode;
  badge: string;
  description: string;
  color: string;
}[] = [
  {
    id: 'normal',
    label: 'Normal Mode',
    shortLabel: 'Normal',
    icon: <Grid className="w-5 h-5" />,
    badge: 'Fixed Layout',
    description: 'Specify an exact photo count, fill individual slots, add captions, download DOCX.',
    color: 'emerald',
  },
  {
    id: 'bulk',
    label: 'Bulk Mode',
    shortLabel: 'Bulk',
    icon: <Layers className="w-5 h-5" />,
    badge: 'Fast Batch',
    description: 'Drop any number of photos at once, drag-to-reorder the queue, auto-number captions.',
    color: 'blue',
  },
  {
    id: 'pro',
    label: 'Pro Studio',
    shortLabel: 'Pro',
    icon: <Zap className="w-5 h-5" />,
    badge: 'Custom Studio',
    description: 'Full DOCX customization: font, borders, compression presets, custom numbering keyword.',
    color: 'amber',
  },
];

const COLOR_CLASSES: Record<string, string> = {
  emerald: 'bg-emerald-50 border-emerald-200 text-emerald-700 hover:bg-emerald-100',
  blue: 'bg-blue-50 border-blue-200 text-blue-700 hover:bg-blue-100',
  amber: 'bg-amber-50 border-amber-200 text-amber-700 hover:bg-amber-100',
};

const ACTIVE_COLOR_CLASSES: Record<string, string> = {
  emerald: 'bg-emerald-600 text-white border-emerald-600 shadow-md',
  blue: 'bg-blue-600 text-white border-blue-600 shadow-md',
  amber: 'bg-amber-600 text-white border-amber-600 shadow-md',
};

export const PhotosPage: React.FC<PhotosPageProps> = ({ reportId, reportNumber, onClose }) => {
  const [selectedMode, setSelectedMode] = useState<Exclude<Mode, null>>('bulk');

  const handleSendToReport = async (photos: ImageData[]) => {
    if (!reportId) {
      alert('No active report. Open a report first, then use Photo Studio from within it to send photos directly.');
      return;
    }

    const formData = new FormData();
    photos.forEach((p) => {
      const blob = p.processedBlob || p.file;
      formData.append('files', new File([blob], p.file.name, { type: 'image/jpeg' }));
    });
    formData.append('series_id', 'survey');
    formData.append('provenance', 'own_survey');

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

    alert(`✓ ${photos.length} photo${photos.length > 1 ? 's' : ''} sent to report ${reportNumber || reportId}.`);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Page Header */}
      <div className="bg-slate-900 text-white border-b border-slate-800 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-600 rounded-xl">
              <Camera className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-lg font-black tracking-tight">Photo Annexure Studio</h1>
                <span className="text-[11px] font-semibold bg-indigo-500/30 text-indigo-200 px-2.5 py-0.5 rounded-full border border-indigo-400/30">
                  Native Client Tool
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {reportId
                  ? `Active Report: ${reportNumber || `#${reportId}`} — photos will be sent to this report`
                  : 'No active report — standalone DOCX generation only'}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white text-xs px-3 py-2 rounded-xl transition cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Reports</span>
          </button>
        </div>

        {/* Mode Tab Bar */}
        <div className="max-w-7xl mx-auto px-4 flex gap-1 pb-0 pt-1">
          {MODES.map((mode) => (
            <button
              key={mode.id}
              type="button"
              onClick={() => setSelectedMode(mode.id)}
              className={`flex items-center gap-2 px-5 py-2.5 text-sm font-semibold rounded-t-xl border-b-2 transition cursor-pointer ${
                selectedMode === mode.id
                  ? 'border-indigo-400 text-white bg-slate-800'
                  : 'border-transparent text-slate-400 hover:text-white hover:bg-slate-800/50'
              }`}
            >
              {mode.icon}
              <span>{mode.label}</span>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                selectedMode === mode.id
                  ? 'bg-indigo-500/30 text-indigo-200 border-indigo-400/30'
                  : 'bg-slate-700 text-slate-400 border-slate-600'
              }`}>
                {mode.badge}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Mode description banner */}
      <div className="max-w-7xl mx-auto w-full px-4 pt-5 pb-2">
        {MODES.map((mode) => (
          selectedMode === mode.id && (
            <div key={mode.id} className={`flex items-start gap-3 p-4 rounded-2xl border text-sm ${
              mode.id === 'normal' ? 'bg-emerald-50 border-emerald-200 text-emerald-800' :
              mode.id === 'bulk'   ? 'bg-blue-50 border-blue-200 text-blue-800' :
                                     'bg-amber-50 border-amber-200 text-amber-800'
            }`}>
              {mode.icon}
              <div>
                <strong>{mode.label}</strong> — {mode.description}
                {!reportId && (
                  <span className="ml-2 text-xs opacity-70">
                    (Open a report first to enable "Send to Report")
                  </span>
                )}
              </div>
            </div>
          )
        ))}
      </div>

      {/* Mode Content */}
      <div className="flex-1 max-w-7xl mx-auto w-full px-4 pb-8">
        <div className="bg-white rounded-2xl border border-gray-200 shadow-xs overflow-hidden">
          {selectedMode === 'normal' && (
            <div className="p-6">
              <NormalMode
                onSendToReport={reportId ? handleSendToReport : undefined}
                reportId={reportId}
              />
            </div>
          )}
          {selectedMode === 'bulk' && (
            <div className="p-6">
              <BulkMode
                onSendToReport={reportId ? handleSendToReport : undefined}
                reportId={reportId}
              />
            </div>
          )}
          {selectedMode === 'pro' && (
            <div className="p-6">
              <ProMode
                onSendToReport={reportId ? handleSendToReport : undefined}
                reportId={reportId}
              />
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 py-3 text-center text-xs text-gray-500">
        Marine Cargo Agencies Private Limited • Bit-Exact Original Photo Storage • SHA-256 Verified
      </footer>
    </div>
  );
};

export default PhotosPage;


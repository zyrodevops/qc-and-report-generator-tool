import React, { useState, useEffect, useCallback } from 'react';
import { AlertTriangle, CheckCircle, ChevronDown, ChevronUp, Loader2, Sparkles } from 'lucide-react';
import {
  fetchClauseTaxonomy,
  CausePattern,
  ClauseTaxonomyCauseResponse,
} from '../../api/client';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
export interface CauseOfLossPickerProps {
  /** Commodity key e.g. "APPLE", "GRAPE" — drives commodity-specific wording */
  commodity?: string;
  /** Called with the canonical legal paragraph when surveyor selects a cause */
  onSelect: (wording: string, causeKey: string, causeLabel: string) => void;
  /** Currently selected cause key (controlled) */
  selectedKey?: string | null;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export const CauseOfLossPicker: React.FC<CauseOfLossPickerProps> = ({
  commodity,
  onSelect,
  selectedKey,
}) => {
  const [open, setOpen] = useState(false);
  const [causes, setCauses] = useState<CausePattern[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewKey, setPreviewKey] = useState<string | null>(null);
  const fetchedFor = React.useRef<string>('');

  const load = useCallback(async () => {
    const cacheKey = commodity ?? '__none__';
    if (fetchedFor.current === cacheKey) return;
    setLoading(true);
    setError(null);
    try {
      const data = (await fetchClauseTaxonomy('cause_of_loss', commodity)) as ClauseTaxonomyCauseResponse;
      setCauses(data.causes);
      fetchedFor.current = cacheKey;
    } catch {
      setError('Unable to load cause patterns. Check backend connection.');
    } finally {
      setLoading(false);
    }
  }, [commodity]);

  const handleToggle = () => {
    if (!open) load();
    setOpen((v) => !v);
  };

  // Reset when commodity changes
  useEffect(() => {
    fetchedFor.current = '';
    setCauses([]);
    setPreviewKey(null);
    setOpen(false);
  }, [commodity]);

  const handleSelect = (cause: CausePattern) => {
    onSelect(cause.wording, cause.key, cause.label);
    setOpen(false);
    setPreviewKey(null);
  };

  const previewedCause = causes.find((c) => c.key === previewKey);
  const selectedCause = causes.find((c) => c.key === selectedKey);

  return (
    <div className="mb-2">
      {/* Trigger button */}
      <button
        type="button"
        onClick={handleToggle}
        className={`
          inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-[10px] font-medium
          border transition-all select-none
          ${open
            ? 'bg-amber-500 text-white border-amber-500 shadow-sm'
            : selectedKey
            ? 'bg-amber-50 text-amber-800 border-amber-300 hover:bg-amber-100'
            : 'bg-white text-amber-700 border-amber-200 hover:bg-amber-50 hover:border-amber-400'
          }
        `}
      >
        <Sparkles size={11} />
        <span>Cause of Loss</span>
        {selectedCause && (
          <span className="opacity-75 font-normal">· {selectedCause.label}</span>
        )}
        {open ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
      </button>

      {/* Panel */}
      {open && (
        <div className="mt-1 border border-amber-200 rounded-lg shadow-xl bg-white overflow-hidden z-50 relative">
          {/* Header */}
          <div className="flex items-center justify-between px-3 py-2 bg-amber-50 border-b border-amber-100">
            <div className="flex items-center gap-1.5">
              <Sparkles size={12} className="text-amber-600" />
              <span className="text-[11px] font-semibold text-amber-900">
                Select Primary Cause of Loss
              </span>
              {commodity && (
                <span className="text-[10px] text-amber-600 font-normal">
                  — {commodity.charAt(0) + commodity.slice(1).toLowerCase()} specific wording
                </span>
              )}
            </div>
            <span className="text-[9px] text-slate-400">click to insert canonical paragraph</span>
          </div>

          {/* Body */}
          <div className="flex max-h-80 overflow-hidden">
            {/* Left: cause list */}
            <div className="w-56 flex-shrink-0 border-r border-slate-100 overflow-y-auto">
              {loading && (
                <div className="flex items-center gap-2 py-6 px-3 text-slate-500 text-xs">
                  <Loader2 size={13} className="animate-spin" />
                  Loading…
                </div>
              )}
              {error && !loading && (
                <div className="flex items-center gap-2 px-3 py-4 text-xs text-red-600">
                  <AlertTriangle size={13} />
                  {error}
                </div>
              )}
              {!loading && !error && causes.map((cause) => {
                const isSelected = selectedKey === cause.key;
                const isPreviewed = previewKey === cause.key;
                return (
                  <button
                    key={cause.key}
                    type="button"
                    className={`
                      w-full text-left px-3 py-2.5 flex items-start gap-2 transition-colors
                      border-b border-slate-50 last:border-b-0
                      ${isSelected
                        ? 'bg-amber-100 border-l-2 border-l-amber-500'
                        : isPreviewed
                        ? 'bg-slate-50'
                        : 'hover:bg-slate-50'
                      }
                    `}
                    onMouseEnter={() => setPreviewKey(cause.key)}
                    onMouseLeave={() => setPreviewKey(null)}
                    onClick={() => handleSelect(cause)}
                  >
                    {/* radio indicator */}
                    <div className={`
                      mt-0.5 flex-shrink-0 w-3.5 h-3.5 rounded-full border-2 flex items-center justify-center
                      ${isSelected
                        ? 'border-amber-500 bg-amber-500'
                        : 'border-slate-300'
                      }
                    `}>
                      {isSelected && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1">
                        <span className="text-[12px]">{cause.icon}</span>
                        <span className={`text-[10px] font-medium leading-tight ${isSelected ? 'text-amber-800' : 'text-slate-700'}`}>
                          {cause.label}
                        </span>
                      </div>
                      <p className="text-[9px] text-slate-400 mt-0.5 leading-tight line-clamp-2">
                        {cause.description}
                      </p>
                      {cause.is_commodity_specific && (
                        <span className="inline-block mt-0.5 text-[8px] bg-green-100 text-green-700 px-1 rounded">
                          {commodity}-specific
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Right: wording preview */}
            <div className="flex-1 p-3 overflow-y-auto">
              {previewedCause ? (
                <div>
                  <div className="flex items-center gap-1 mb-2">
                    <span className="text-[13px]">{previewedCause.icon}</span>
                    <span className="text-[10px] font-semibold text-slate-800">
                      {previewedCause.label}
                    </span>
                    {previewedCause.is_commodity_specific && (
                      <span className="text-[9px] bg-green-100 text-green-700 px-1 rounded ml-1">
                        commodity-specific
                      </span>
                    )}
                  </div>
                  <p className="text-[10px] leading-relaxed text-slate-700 text-justify whitespace-pre-wrap">
                    {previewedCause.wording}
                  </p>
                  <button
                    type="button"
                    onClick={() => handleSelect(previewedCause)}
                    className="mt-2 inline-flex items-center gap-1 px-2 py-1 bg-amber-500 text-white rounded text-[10px] font-medium hover:bg-amber-600 transition-colors"
                  >
                    <CheckCircle size={10} />
                    Insert this wording
                  </button>
                </div>
              ) : selectedCause ? (
                <div>
                  <div className="flex items-center gap-1 mb-1">
                    <CheckCircle size={11} className="text-amber-500" />
                    <span className="text-[10px] font-medium text-amber-800">Currently selected:</span>
                  </div>
                  <p className="text-[10px] leading-relaxed text-slate-600 text-justify">
                    {selectedCause.wording}
                  </p>
                  <p className="mt-2 text-[9px] text-slate-400">Hover a cause on the left to preview alternative wording.</p>
                </div>
              ) : (
                <p className="text-[10px] text-slate-400 pt-4 text-center">
                  Hover a cause pattern on the left to preview the canonical legal paragraph.
                </p>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="px-3 py-1.5 bg-slate-50 border-t border-slate-100 text-[9px] text-slate-400">
            Selecting a cause inserts the canonical paragraph. You can edit it freely afterwards in the text area.
          </div>
        </div>
      )}
    </div>
  );
};


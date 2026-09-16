import React, { useState, useEffect, useCallback } from 'react';
import { AlertTriangle, CheckSquare, ChevronDown, ChevronUp, Loader2, ListChecks } from 'lucide-react';
import {
  fetchClauseTaxonomy,
  NextStepAction,
  ClauseTaxonomyNextStepResponse,
} from '../../api/client';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
export interface NextStepPickerProps {
  /** Commodity key e.g. "APPLE", "GRAPE" — filters applicable actions */
  commodity?: string;
  /**
   * Called when the surveyor clicks "Insert Actions".
   * Receives the fully assembled multi-line next-step paragraph.
   */
  onAssemble: (text: string) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export const NextStepPicker: React.FC<NextStepPickerProps> = ({
  commodity,
  onAssemble,
}) => {
  const [open, setOpen] = useState(false);
  const [actions, setActions] = useState<NextStepAction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const fetchedFor = React.useRef<string>('');

  const load = useCallback(async () => {
    const cacheKey = commodity ?? '__none__';
    if (fetchedFor.current === cacheKey) return;
    setLoading(true);
    setError(null);
    try {
      const data = (await fetchClauseTaxonomy('next_step', commodity)) as ClauseTaxonomyNextStepResponse;
      setActions(data.actions);
      // Pre-check applicable actions that are most universal
      const defaultChecked = new Set<string>();
      data.actions.forEach((a) => {
        if (a.is_applicable && (a.key === 'NOTICE_TO_CARRIER' || a.key === 'FURTHER_SURVEY')) {
          defaultChecked.add(a.key);
        }
      });
      setChecked(defaultChecked);
      fetchedFor.current = cacheKey;
    } catch {
      setError('Unable to load next-step actions. Check backend connection.');
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
    setActions([]);
    setChecked(new Set());
    setOpen(false);
  }, [commodity]);

  const toggleAction = (key: string) => {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const handleInsert = () => {
    const selectedActions = actions.filter((a) => checked.has(a.key));
    if (selectedActions.length === 0) return;

    // Build numbered list if multiple, or single sentence if one
    const lines = selectedActions.map((a, i) =>
      selectedActions.length > 1 ? `${i + 1}. ${a.text}` : a.text
    );
    onAssemble(lines.join('\n\n'));
    setOpen(false);
  };

  const checkedCount = actions.filter((a) => checked.has(a.key)).length;
  const applicableActions = actions.filter((a) => a.is_applicable);
  const inapplicableActions = actions.filter((a) => !a.is_applicable);

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
            ? 'bg-teal-600 text-white border-teal-600 shadow-sm'
            : 'bg-white text-teal-700 border-teal-200 hover:bg-teal-50 hover:border-teal-400'
          }
        `}
      >
        <ListChecks size={11} />
        <span>Next Step Actions</span>
        {open ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
      </button>

      {/* Panel */}
      {open && (
        <div className="mt-1 border border-teal-200 rounded-lg shadow-xl bg-white overflow-hidden z-50 relative">
          {/* Header */}
          <div className="flex items-center justify-between px-3 py-2 bg-teal-50 border-b border-teal-100">
            <div className="flex items-center gap-1.5">
              <ListChecks size={12} className="text-teal-600" />
              <span className="text-[11px] font-semibold text-teal-900">
                Select Next Step Recommendations
              </span>
            </div>
            <span className="text-[9px] text-slate-400">checked items are assembled into the text</span>
          </div>

          {/* Body */}
          <div className="max-h-80 overflow-y-auto divide-y divide-slate-50">
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

            {!loading && !error && (
              <>
                {applicableActions.map((action) => {
                  const isChecked = checked.has(action.key);
                  return (
                    <label
                      key={action.key}
                      className={`
                        flex items-start gap-2.5 px-3 py-2.5 cursor-pointer transition-colors
                        ${isChecked ? 'bg-teal-50' : 'hover:bg-slate-50'}
                      `}
                    >
                      <div className="mt-0.5 flex-shrink-0">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => toggleAction(action.key)}
                          className="accent-teal-600 w-3.5 h-3.5"
                        />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-[10px] font-medium ${isChecked ? 'text-teal-800' : 'text-slate-700'}`}>
                          {action.label}
                        </p>
                        <p className="text-[9px] text-slate-400 mt-0.5 leading-relaxed">
                          {action.text}
                        </p>
                      </div>
                    </label>
                  );
                })}

                {inapplicableActions.length > 0 && (
                  <details className="group">
                    <summary className="px-3 py-2 text-[9px] text-slate-400 cursor-pointer list-none flex items-center gap-1 hover:bg-slate-50">
                      <ChevronDown size={9} className="group-open:rotate-180 transition-transform" />
                      {inapplicableActions.length} additional actions (less common for {commodity ?? 'this commodity'})
                    </summary>
                    {inapplicableActions.map((action) => {
                      const isChecked = checked.has(action.key);
                      return (
                        <label
                          key={action.key}
                          className={`
                            flex items-start gap-2.5 px-3 py-2.5 cursor-pointer transition-colors opacity-70
                            ${isChecked ? 'bg-teal-50 opacity-100' : 'hover:bg-slate-50'}
                          `}
                        >
                          <div className="mt-0.5 flex-shrink-0">
                            <input
                              type="checkbox"
                              checked={isChecked}
                              onChange={() => toggleAction(action.key)}
                              className="accent-teal-600 w-3.5 h-3.5"
                            />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-[10px] font-medium text-slate-600">{action.label}</p>
                            <p className="text-[9px] text-slate-400 mt-0.5 leading-relaxed">
                              {action.text}
                            </p>
                          </div>
                        </label>
                      );
                    })}
                  </details>
                )}
              </>
            )}
          </div>

          {/* Footer with insert button */}
          <div className="px-3 py-2 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
            <span className="text-[9px] text-slate-400">
              {checkedCount > 0
                ? `${checkedCount} action${checkedCount !== 1 ? 's' : ''} selected — will be assembled as a numbered list`
                : 'Select one or more actions to insert'}
            </span>
            <button
              type="button"
              disabled={checkedCount === 0}
              onClick={handleInsert}
              className={`
                inline-flex items-center gap-1 px-2.5 py-1 rounded text-[10px] font-medium transition-colors
                ${checkedCount > 0
                  ? 'bg-teal-600 text-white hover:bg-teal-700'
                  : 'bg-slate-200 text-slate-400 cursor-not-allowed'
                }
              `}
            >
              <CheckSquare size={10} />
              Insert {checkedCount > 0 ? `${checkedCount} Action${checkedCount !== 1 ? 's' : ''}` : 'Actions'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

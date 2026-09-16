/**
 * BoilerplatePicker — renamed and cleaned-up version of ClauseLibraryPicker.
 * Used for sections other than cause_of_loss and next_step (circumstances_of_loss,
 * survey_findings, documentation, general), where a flat corpus frequency list is appropriate.
 */
import React, { useState, useCallback, useRef, useEffect } from 'react';
import { BookOpen, ChevronDown, ChevronUp, Plus, Loader2, AlertCircle } from 'lucide-react';
import { fetchClauses, Clause } from '../../api/client';

// ---------------------------------------------------------------------------
// Section slug detection from heading text (shared utility)
// ---------------------------------------------------------------------------
export const HEADING_TO_SECTION: [RegExp, string][] = [
  [/circumstance|circumstances of loss/i, 'circumstances_of_loss'],
  [/cause of loss|cause \& liability/i, 'cause_of_loss'],
  [/our survey|survey.*finding|findings|condition found/i, 'survey_findings'],
  [/next step/i, 'next_step'],
  [/document|annexure|enclosure/i, 'documentation'],
];

export function detectSectionFromHeading(heading: string): string {
  for (const [pattern, slug] of HEADING_TO_SECTION) {
    if (pattern.test(heading)) return slug;
  }
  return 'general';
}

export const SECTION_LABELS: Record<string, string> = {
  circumstances_of_loss: 'Circumstances of Loss',
  cause_of_loss: 'Cause of Loss',
  survey_findings: 'Survey Findings',
  next_step: 'Next Step',
  documentation: 'Documentation',
  general: 'General',
};

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
export interface BoilerplatePickerProps {
  commodity?: string;
  sectionHeading?: string;
  onInsert: (text: string) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export const BoilerplatePicker: React.FC<BoilerplatePickerProps> = ({
  commodity,
  sectionHeading = '',
  onInsert,
}) => {
  const section = detectSectionFromHeading(sectionHeading);
  const [open, setOpen] = useState(false);
  const [clauses, setClauses] = useState<Clause[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inserted, setInserted] = useState<Set<string>>(new Set());
  const panelRef = useRef<HTMLDivElement>(null);
  const fetchedKey = useRef<string>('');

  const loadClauses = useCallback(async () => {
    const key = `${commodity}__${section}`;
    if (fetchedKey.current === key) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchClauses(commodity, section === 'general' ? undefined : section, 10);
      setClauses(data);
      fetchedKey.current = key;
    } catch {
      setError('Unable to load clause library. Check backend connection.');
    } finally {
      setLoading(false);
    }
  }, [commodity, section]);

  const handleToggle = () => {
    if (!open) loadClauses();
    setOpen((v) => !v);
  };

  const handleInsert = (clause: Clause) => {
    onInsert(clause.text);
    setInserted((prev) => new Set(prev).add(clause.text));
  };

  // Close on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    if (open) document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  // Reset on commodity/section change
  useEffect(() => {
    setInserted(new Set());
    setOpen(false);
    fetchedKey.current = '';
    setClauses([]);
  }, [commodity, sectionHeading]);

  const sectionLabel = SECTION_LABELS[section] ?? 'General';
  const hasCommodity = Boolean(commodity && commodity !== 'GENERAL_CARGO');

  return (
    <div ref={panelRef} className="relative mb-1">
      {/* Toggle button */}
      <button
        type="button"
        onClick={handleToggle}
        title={
          hasCommodity
            ? `Clause library for ${commodity} — ${sectionLabel}`
            : 'Clause library — common narrative paragraphs'
        }
        className={`
          inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-[10px] font-medium
          border transition-all select-none
          ${open
            ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
            : 'bg-white text-blue-700 border-blue-200 hover:bg-blue-50 hover:border-blue-400'
          }
        `}
      >
        <BookOpen size={11} />
        <span>Clause Library</span>
        {hasCommodity && (
          <span className="opacity-70 font-normal">
            · {commodity!.charAt(0) + commodity!.slice(1).toLowerCase()}
          </span>
        )}
        {open ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
      </button>

      {/* Dropdown panel */}
      {open && (
        <div
          className="absolute left-0 top-full mt-1 z-50 w-[520px] max-w-[90vw]
                     bg-white border border-blue-200 rounded-lg shadow-xl overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-3 py-2 bg-blue-50 border-b border-blue-100">
            <div className="flex items-center gap-1.5">
              <BookOpen size={12} className="text-blue-600" />
              <span className="text-[11px] font-semibold text-blue-800">
                {hasCommodity
                  ? `${commodity!.charAt(0) + commodity!.slice(1).toLowerCase()} — ${sectionLabel}`
                  : sectionLabel}
              </span>
              <span className="text-[10px] text-blue-500 font-normal">
                (click to insert)
              </span>
            </div>
            <span className="text-[10px] text-slate-400">from real client reports</span>
          </div>

          {/* Body */}
          <div className="max-h-72 overflow-y-auto">
            {loading && (
              <div className="flex items-center justify-center gap-2 py-6 text-slate-500 text-xs">
                <Loader2 size={14} className="animate-spin" />
                Loading corpus clauses…
              </div>
            )}
            {error && !loading && (
              <div className="flex items-center gap-2 px-3 py-4 text-xs text-red-600">
                <AlertCircle size={13} />
                {error}
              </div>
            )}
            {!loading && !error && clauses.length === 0 && (
              <div className="px-3 py-4 text-xs text-slate-400 text-center">
                No clauses found for this section.
              </div>
            )}
            {!loading && !error && clauses.length > 0 && (
              <ul className="divide-y divide-slate-100">
                {clauses.map((clause, idx) => {
                  const alreadyInserted = inserted.has(clause.text);
                  return (
                    <li
                      key={idx}
                      className={`
                        group flex items-start gap-2 px-3 py-2.5 cursor-pointer
                        transition-colors hover:bg-blue-50
                        ${alreadyInserted ? 'bg-green-50' : ''}
                      `}
                      onClick={() => handleInsert(clause)}
                      title="Click to append this clause to the text area"
                    >
                      <div className={`
                        flex-shrink-0 mt-0.5 w-5 h-5 rounded flex items-center justify-center
                        ${alreadyInserted
                          ? 'bg-green-100 text-green-600'
                          : 'bg-slate-100 text-slate-400 group-hover:bg-blue-100 group-hover:text-blue-600'
                        }
                      `}>
                        <Plus size={11} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`
                          text-[11px] leading-relaxed line-clamp-3
                          ${alreadyInserted ? 'text-green-700' : 'text-slate-700 group-hover:text-slate-900'}
                        `}>
                          {clause.text.split(/(\[.*?\])/g).map((part, i) =>
                            /^\[.*\]$/.test(part) ? (
                              <mark
                                key={i}
                                className="bg-amber-100 text-amber-800 rounded px-0.5 not-italic font-medium"
                              >
                                {part}
                              </mark>
                            ) : part
                          )}
                        </p>
                        <div className="flex items-center gap-2 mt-1">
                          {clause.count > 0 && (
                            <span className="text-[9px] text-slate-400">
                              Used in {clause.count} report{clause.count !== 1 ? 's' : ''}
                            </span>
                          )}
                          {clause.is_template && (
                            <span className="text-[9px] bg-amber-100 text-amber-700 px-1 rounded">
                              fill in required
                            </span>
                          )}
                          {alreadyInserted && (
                            <span className="text-[9px] text-green-600 font-medium">✓ inserted</span>
                          )}
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          {/* Footer */}
          <div className="px-3 py-1.5 bg-slate-50 border-t border-slate-100 text-[9px] text-slate-400">
            Clauses are appended to the text area. Edit them after inserting.
            {hasCommodity && (
              <> Showing clauses relevant to{' '}
                <strong>{commodity!.charAt(0) + commodity!.slice(1).toLowerCase()}</strong>
                {section !== 'general' && <> in the <strong>{sectionLabel}</strong> section</>}.
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

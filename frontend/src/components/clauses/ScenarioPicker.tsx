import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Compass, ChevronDown, ChevronUp, CheckCircle, Loader2, AlertCircle, FileText } from 'lucide-react';
import { fetchClauseTaxonomy, NarrativeScenario, ClauseTaxonomyScenarioResponse } from '../../api/client';

export interface ScenarioPickerProps {
  commodity?: string;
  sectionSlug: string;
  sectionLabel: string;
  onSelect: (text: string) => void;
}

export const ScenarioPicker: React.FC<ScenarioPickerProps> = ({
  commodity,
  sectionSlug,
  sectionLabel,
  onSelect,
}) => {
  const [open, setOpen] = useState(false);
  const [scenarios, setScenarios] = useState<NarrativeScenario[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewKey, setPreviewKey] = useState<string | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const fetchedKey = useRef<string>('');

  const loadScenarios = useCallback(async () => {
    const key = `${commodity}__${sectionSlug}`;
    if (fetchedKey.current === key) return;
    setLoading(true);
    setError(null);
    try {
      const data = (await fetchClauseTaxonomy(sectionSlug, commodity)) as ClauseTaxonomyScenarioResponse;
      setScenarios(data.scenarios || []);
      if (data.scenarios && data.scenarios.length > 0) {
        setPreviewKey(data.scenarios[0].key);
      }
      fetchedKey.current = key;
    } catch {
      setError(`Unable to load scenarios for ${sectionLabel}.`);
    } finally {
      setLoading(false);
    }
  }, [commodity, sectionSlug, sectionLabel]);

  const handleToggle = () => {
    if (!open) loadScenarios();
    setOpen((v) => !v);
  };

  const handleInsert = (scenario: NarrativeScenario) => {
    onSelect(scenario.template);
    setOpen(false);
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

  // Reset when section or commodity changes
  useEffect(() => {
    setOpen(false);
    fetchedKey.current = '';
    setScenarios([]);
    setPreviewKey(null);
  }, [commodity, sectionSlug]);

  const previewed = scenarios.find((s) => s.key === previewKey) || scenarios[0];
  const commodityName = commodity ? commodity.charAt(0) + commodity.slice(1).toLowerCase() : 'Fruit';

  return (
    <div ref={panelRef} className="relative mb-2">
      {/* Trigger button */}
      <button
        type="button"
        onClick={handleToggle}
        className={`
          inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-semibold
          border transition-all select-none shadow-sm
          ${open
            ? 'bg-indigo-600 text-white border-indigo-600 shadow'
            : 'bg-indigo-50 text-indigo-700 border-indigo-200 hover:bg-indigo-100 hover:border-indigo-400'
          }
        `}
      >
        <Compass size={12} className={open ? 'text-white' : 'text-indigo-600'} />
        <span>Select {sectionLabel} Scenario</span>
        <span className="opacity-70 font-normal">({commodityName})</span>
        {open ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
      </button>

      {/* Dropdown panel */}
      {open && (
        <div
          className="absolute left-0 top-full mt-1 z-50 w-[720px] max-w-[95vw]
                     bg-white border border-indigo-200 rounded-xl shadow-2xl overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-2.5 bg-gradient-to-r from-indigo-50 to-blue-50 border-b border-indigo-100">
            <div className="flex items-center gap-2">
              <Compass size={14} className="text-indigo-600" />
              <span className="text-xs font-bold text-indigo-900">
                {sectionLabel} — Recommended Client Scenarios ({commodityName})
              </span>
            </div>
            <span className="text-[10px] text-indigo-600 font-medium bg-white px-2 py-0.5 rounded-full border border-indigo-100 shadow-2xs">
              Mined from 432 Client Reports
            </span>
          </div>

          {/* Body with Left: scenario cards, Right: full text preview */}
          <div className="flex max-h-[360px] overflow-hidden">
            {/* Left Column: Scenario Options */}
            <div className="w-[300px] flex-shrink-0 border-r border-slate-100 overflow-y-auto bg-slate-50/50 p-2 space-y-1.5">
              {loading && (
                <div className="flex items-center justify-center gap-2 py-10 text-slate-500 text-xs">
                  <Loader2 size={16} className="animate-spin text-indigo-600" />
                  Loading client scenarios…
                </div>
              )}

              {error && !loading && (
                <div className="flex items-center gap-2 p-3 text-xs text-red-600 bg-red-50 rounded-lg">
                  <AlertCircle size={14} />
                  {error}
                </div>
              )}

              {!loading && !error && scenarios.map((scenario) => {
                const isSelected = previewKey === scenario.key;
                return (
                  <div
                    key={scenario.key}
                    onClick={() => setPreviewKey(scenario.key)}
                    className={`
                      p-2.5 rounded-lg border cursor-pointer transition-all text-left
                      ${isSelected
                        ? 'bg-white border-indigo-500 shadow-xs ring-1 ring-indigo-500'
                        : 'bg-white/80 border-slate-200 hover:border-indigo-300 hover:bg-white'
                      }
                    `}
                  >
                    <div className="flex items-center justify-between gap-1 mb-1">
                      <span className="text-[11px] font-bold text-slate-800 leading-tight">
                        {scenario.label}
                      </span>
                      {scenario.badge && (
                        <span className="text-[9px] font-semibold uppercase tracking-wider bg-indigo-100 text-indigo-700 px-1.5 py-0.2 rounded">
                          {scenario.badge}
                        </span>
                      )}
                    </div>
                    <p className="text-[10px] text-slate-500 line-clamp-2 leading-relaxed">
                      {scenario.description}
                    </p>
                  </div>
                );
              })}
            </div>

            {/* Right Column: Full Text Preview & Insert */}
            <div className="flex-1 p-4 overflow-y-auto flex flex-col justify-between bg-white">
              {previewed ? (
                <div>
                  <div className="flex items-center justify-between pb-2 mb-3 border-b border-slate-100">
                    <div>
                      <h4 className="text-xs font-bold text-slate-900">{previewed.label}</h4>
                      <p className="text-[10px] text-slate-500">{previewed.description}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleInsert(previewed)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors cursor-pointer"
                    >
                      <CheckCircle size={13} />
                      Insert This Scenario
                    </button>
                  </div>

                  <div className="bg-slate-50 rounded-lg p-3 border border-slate-200 text-xs leading-relaxed text-slate-800 font-sans text-justify max-h-[220px] overflow-y-auto">
                    {/* Render with highlighted placeholders */}
                    {previewed.template.split(/(\[.*?\])/g).map((part, i) =>
                      /^\[.*\]$/.test(part) ? (
                        <mark
                          key={i}
                          className="bg-amber-100 text-amber-900 rounded px-1 font-semibold not-italic"
                        >
                          {part}
                        </mark>
                      ) : (
                        part
                      )
                    )}
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-xs text-slate-400">
                  Select a scenario on the left to preview the paragraph.
                </div>
              )}

              {/* Footer hint */}
              <div className="pt-3 mt-3 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-400">
                <span>Placeholders like <span className="bg-amber-100 text-amber-800 px-1 rounded font-mono font-bold">[VESSEL NAME]</span> can be edited in the text area.</span>
                {previewed && (
                  <button
                    type="button"
                    onClick={() => handleInsert(previewed)}
                    className="text-indigo-600 font-bold hover:underline"
                  >
                    Click to insert →
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};


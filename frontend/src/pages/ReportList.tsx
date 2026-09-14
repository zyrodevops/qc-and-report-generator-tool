import React, { useState, useEffect } from 'react';
import {
  FileText,
  Plus,
  Ship,
  Plane,
  Calendar,
  ArrowRight,
  Loader2,
  CheckCircle2,
  Info,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { fetchReports, createReport, fetchCommodities, ReportSummary, CommodityArchetype } from '../api/client';

interface ReportListProps {
  onSelectReport: (report: ReportSummary) => void;
}

const REPORT_TYPE_OPTIONS = [
  { value: 'perishable-qc-sea', label: 'Perishable QC Report – Sea', family: 'QC_REPORT', mode: 'SEA' },
  { value: 'perishable-qc-air', label: 'Perishable QC Report – Air', family: 'QC_REPORT', mode: 'AIR' },
  { value: 'perishable-survey-sea', label: 'Perishable Survey – Sea', family: 'SURVEY_REPORT', mode: 'SEA' },
  { value: 'perishable-survey-air', label: 'Perishable Survey – Air', family: 'SURVEY_REPORT', mode: 'AIR' },
  { value: 'general-cargo-sea', label: 'General Cargo Survey – Sea', family: 'SURVEY_REPORT', mode: 'SEA' },
  { value: 'general-cargo-air', label: 'General Cargo Survey – Air', family: 'SURVEY_REPORT', mode: 'AIR' },
];

// Color mapping for commodity pills
const COLOR_CLASSES: Record<string, { bg: string; border: string; text: string; badge: string }> = {
  red:    { bg: 'bg-red-50',     border: 'border-red-400',    text: 'text-red-800',    badge: 'bg-red-100 text-red-700' },
  orange: { bg: 'bg-orange-50',  border: 'border-orange-400', text: 'text-orange-800', badge: 'bg-orange-100 text-orange-700' },
  green:  { bg: 'bg-green-50',   border: 'border-green-400',  text: 'text-green-800',  badge: 'bg-green-100 text-green-700' },
  blue:   { bg: 'bg-blue-50',    border: 'border-blue-400',   text: 'text-blue-800',   badge: 'bg-blue-100 text-blue-700' },
  purple: { bg: 'bg-purple-50',  border: 'border-purple-400', text: 'text-purple-800', badge: 'bg-purple-100 text-purple-700' },
  pink:   { bg: 'bg-pink-50',    border: 'border-pink-400',   text: 'text-pink-800',   badge: 'bg-pink-100 text-pink-700' },
  gray:   { bg: 'bg-gray-50',    border: 'border-gray-400',   text: 'text-gray-800',   badge: 'bg-gray-100 text-gray-700' },
};

export const ReportList: React.FC<ReportListProps> = ({ onSelectReport }) => {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [creating, setCreating] = useState(false);

  // Commodity data from backend
  const [commodities, setCommodities] = useState<CommodityArchetype[]>([]);
  const [commoditiesLoading, setCommoditiesLoading] = useState(false);
  const [expandedCommodity, setExpandedCommodity] = useState<string | null>(null);

  // New report form state
  const [selectedTemplate, setSelectedTemplate] = useState('perishable-qc-sea');
  const [selectedMode, setSelectedMode] = useState<'SEA' | 'AIR'>('SEA');
  const [selectedFamily, setSelectedFamily] = useState('QC_REPORT');
  const [selectedCommodity, setSelectedCommodity] = useState('APPLE');
  const [year, setYear] = useState(new Date().getFullYear());

  const loadReports = async () => {
    try {
      setLoading(true);
      const data = await fetchReports();
      setReports(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadCommodities = async () => {
    try {
      setCommoditiesLoading(true);
      const data = await fetchCommodities();
      setCommodities(data);
      // Default-select the first (most common) commodity
      if (data.length > 0) setSelectedCommodity(data[0].key);
    } catch (err) {
      console.error('Could not load commodities:', err);
    } finally {
      setCommoditiesLoading(false);
    }
  };

  useEffect(() => {
    loadReports();
  }, []);

  const handleOpenModal = () => {
    setShowModal(true);
    if (commodities.length === 0) loadCommodities();
  };

  const handleTemplateChange = (val: string) => {
    const opt = REPORT_TYPE_OPTIONS.find((o) => o.value === val);
    if (opt) {
      setSelectedTemplate(val);
      setSelectedFamily(opt.family);
      setSelectedMode(opt.mode as 'SEA' | 'AIR');
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setCreating(true);
      const newRep = await createReport({
        template_id: selectedTemplate,
        family: selectedFamily,
        mode: selectedMode,
        commodity: selectedCommodity.toLowerCase(),
        year: Number(year),
      });
      setShowModal(false);
      onSelectReport(newRep);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setCreating(false);
    }
  };

  const selectedCommodityData = commodities.find((c) => c.key === selectedCommodity);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap justify-between items-center gap-4 bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
        <div>
          <h1 className="text-2xl font-black text-gray-900 tracking-tight">Marine Cargo Survey Reports</h1>
          <p className="text-sm text-gray-500 mt-1">
            IRDAI-Licensed Marine Cargo Agencies — QC &amp; Survey Report Platform
          </p>
        </div>
        <button
          onClick={handleOpenModal}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold px-4 py-2.5 rounded-lg shadow-sm transition"
        >
          <Plus className="w-5 h-5" />
          Create New Report
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center p-12 text-gray-500 gap-2">
          <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
          <span>Loading surveyor reports...</span>
        </div>
      ) : reports.length === 0 ? (
        <div className="bg-white rounded-xl border border-dashed border-gray-300 p-12 text-center space-y-3">
          <FileText className="w-12 h-12 text-gray-400 mx-auto" />
          <h3 className="text-lg font-bold text-gray-800">No survey reports created yet</h3>
          <p className="text-sm text-gray-500 max-w-md mx-auto">
            Click &quot;Create New Report&quot; to initialize a new survey with automated gapless M-&lt;n&gt;-{year} numbering.
          </p>
          <button
            onClick={handleOpenModal}
            className="inline-flex items-center gap-2 bg-blue-600 text-white font-medium px-4 py-2 rounded-lg text-sm transition hover:bg-blue-700"
          >
            <Plus className="w-4 h-4" />
            Create First Report
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {reports.map((rep) => {
            const mode = rep.block_state?.transport?.mode || 'SEA';
            return (
              <div
                key={rep.id}
                onClick={() => onSelectReport(rep)}
                className="bg-white rounded-xl border border-gray-200 p-5 hover:border-blue-500 hover:shadow-md transition cursor-pointer flex flex-col justify-between group"
              >
                <div className="space-y-3">
                  <div className="flex justify-between items-start">
                    <span className="font-mono font-bold text-lg text-blue-900 tracking-wide">
                      {rep.report_number}
                    </span>
                    <span
                      className={`text-xs px-2.5 py-0.5 rounded-full font-semibold flex items-center gap-1 ${
                        mode === 'SEA'
                          ? 'bg-blue-50 text-blue-700 border border-blue-200'
                          : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      }`}
                    >
                      {mode === 'SEA' ? <Ship className="w-3.5 h-3.5" /> : <Plane className="w-3.5 h-3.5" />}
                      {mode}
                    </span>
                  </div>

                  <div>
                    <h3 className="font-semibold text-gray-900 text-base">
                      {rep.template_id.replace(/-/g, ' ').toUpperCase()}
                    </h3>
                    <p className="text-xs text-gray-500 mt-0.5">Family: {rep.family}</p>
                  </div>
                </div>

                <div className="pt-4 mt-4 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">
                  <div className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5 text-gray-400" />
                    <span>{new Date(rep.created_at).toLocaleDateString()}</span>
                  </div>
                  <span className="text-blue-600 font-semibold group-hover:translate-x-1 transition-transform flex items-center gap-1">
                    Open Form <ArrowRight className="w-3.5 h-3.5" />
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* CREATE REPORT MODAL                                                 */}
      {/* ------------------------------------------------------------------ */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-xs flex items-start justify-center p-4 z-50 overflow-y-auto">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-5 my-6">
            <div className="flex justify-between items-center pb-3 border-b border-gray-100">
              <h2 className="text-xl font-bold text-gray-900">New Marine Cargo Survey Report</h2>
              <button
                onClick={() => setShowModal(false)}
                className="text-gray-400 hover:text-gray-600 text-2xl font-light leading-none"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-5">

              {/* ── Report type ──────────────────────────────────────────── */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">
                  Report Type
                </label>
                <select
                  value={selectedTemplate}
                  onChange={(e) => handleTemplateChange(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                >
                  {REPORT_TYPE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>

              {/* ── Commodity picker ─────────────────────────────────────── */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Commodity &amp; Defect Preset
                  <span className="ml-2 text-xs font-normal text-gray-400">
                    — mined from {commodities.reduce((s, c) => s + c.report_count, 0)} real client reports
                  </span>
                </label>

                {commoditiesLoading ? (
                  <div className="flex items-center gap-2 text-sm text-gray-500 py-4">
                    <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                    Loading commodity templates…
                  </div>
                ) : commodities.length === 0 ? (
                  <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3">
                    Corpus mining output not found. Run <code>tools/mine_corpus.py</code> to generate commodity presets.
                  </div>
                ) : (
                  <>
                    {/* Grid of commodity cards */}
                    <div className="grid grid-cols-3 sm:grid-cols-4 gap-2 max-h-56 overflow-y-auto pr-1">
                      {commodities.map((c) => {
                        const colors = COLOR_CLASSES[c.color] || COLOR_CLASSES.gray;
                        const isSelected = selectedCommodity === c.key;
                        return (
                          <button
                            key={c.key}
                            type="button"
                            onClick={() => {
                              setSelectedCommodity(c.key);
                              setExpandedCommodity(expandedCommodity === c.key ? null : c.key);
                            }}
                            className={`relative flex flex-col items-center gap-1 p-2.5 rounded-xl border-2 text-center transition
                              ${isSelected
                                ? `${colors.bg} ${colors.border} ring-2 ring-offset-1 ring-blue-400`
                                : 'bg-white border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                              }`}
                          >
                            {isSelected && (
                              <CheckCircle2 className="absolute top-1.5 right-1.5 w-3.5 h-3.5 text-blue-500" />
                            )}
                            <span className="text-2xl leading-none">{c.emoji}</span>
                            <span className={`text-xs font-bold leading-tight ${isSelected ? colors.text : 'text-gray-700'}`}>
                              {c.display}
                            </span>
                            <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${isSelected ? colors.badge : 'bg-gray-100 text-gray-500'}`}>
                              {c.report_count} reports
                            </span>
                          </button>
                        );
                      })}
                    </div>

                    {/* Expanded detail panel for selected commodity */}
                    {selectedCommodityData && (
                      <div className="mt-3 bg-gray-50 border border-gray-200 rounded-xl p-4 space-y-3 text-xs">
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <p className="font-bold text-gray-800 text-sm">
                              {selectedCommodityData.emoji} {selectedCommodityData.display}
                              <span className="ml-2 font-normal text-gray-500">· unit: {selectedCommodityData.unit}</span>
                            </p>
                            <p className="text-gray-500 mt-0.5">
                              Based on <strong>{selectedCommodityData.report_count}</strong> real client reports
                            </p>
                          </div>
                          <Info className="w-4 h-4 text-gray-400 shrink-0 mt-0.5" />
                        </div>

                        {/* Defect columns */}
                        <div>
                          <p className="font-semibold text-gray-700 mb-1.5">Defect Columns (auto-prefilled):</p>
                          <div className="flex flex-wrap gap-1.5">
                            {selectedCommodityData.defect_columns.map((col) => (
                              <span key={col} className="bg-white border border-gray-300 text-gray-700 px-2 py-0.5 rounded-md font-mono text-[10px]">
                                {col}
                              </span>
                            ))}
                          </div>
                        </div>

                        {/* Section sequence */}
                        <div>
                          <button
                            type="button"
                            onClick={() => setExpandedCommodity(expandedCommodity === 'seq' ? null : 'seq')}
                            className="flex items-center gap-1 text-gray-600 font-semibold hover:text-gray-900 transition"
                          >
                            Report Sections
                            {expandedCommodity === 'seq' ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                          </button>
                          {expandedCommodity === 'seq' && (
                            <ol className="mt-1.5 space-y-0.5 pl-4 list-decimal text-gray-600">
                              {selectedCommodityData.heading_sequence.map((h, i) => (
                                <li key={i}>{h}</li>
                              ))}
                            </ol>
                          )}
                        </div>

                        {/* Top narrative clause preview */}
                        {selectedCommodityData.top_narrative_clauses.length > 0 && (
                          <div>
                            <p className="font-semibold text-gray-700 mb-1">Common Wording (pre-filled):</p>
                            <p className="italic text-gray-600 leading-relaxed line-clamp-2">
                              "{selectedCommodityData.top_narrative_clauses[0]}"
                            </p>
                          </div>
                        )}
                      </div>
                    )}
                  </>
                )}
              </div>

              {/* ── Transport mode + year ────────────────────────────────── */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1">Transport Mode</label>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setSelectedMode('SEA')}
                      className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg border text-sm font-semibold transition ${
                        selectedMode === 'SEA'
                          ? 'bg-blue-50 border-blue-500 text-blue-700'
                          : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50'
                      }`}
                    >
                      <Ship className="w-4 h-4" />
                      Sea
                    </button>
                    <button
                      type="button"
                      onClick={() => setSelectedMode('AIR')}
                      className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg border text-sm font-semibold transition ${
                        selectedMode === 'AIR'
                          ? 'bg-emerald-50 border-emerald-500 text-emerald-700'
                          : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50'
                      }`}
                    >
                      <Plane className="w-4 h-4" />
                      Air
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1">Sequence Year</label>
                  <input
                    type="number"
                    value={year}
                    onChange={(e) => setYear(Number(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none font-mono"
                  />
                </div>
              </div>

              {/* ── Info banner ──────────────────────────────────────────── */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-800">
                <p className="font-semibold">Sequential Number Allocation:</p>
                <p className="mt-0.5">
                  The server atomically issues consecutive <code className="font-mono">M-&lt;n&gt;-{year}</code> without gaps or duplicates under concurrency.
                  Commodity preset auto-populates section headings, defect columns, and narrative wording.
                </p>
              </div>

              <div className="flex justify-end gap-3 pt-2 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold px-5 py-2 rounded-lg text-sm transition shadow-sm disabled:opacity-50"
                >
                  {creating && <Loader2 className="w-4 h-4 animate-spin" />}
                  Allocate &amp; Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

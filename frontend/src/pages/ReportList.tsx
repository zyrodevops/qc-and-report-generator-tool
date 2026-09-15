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
  CheckSquare,
  Square,
  SlidersHorizontal,
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

export const GENERAL_CARGO_SECTIONS = [
  { id: 'particulars', label: '1. Consignment Particulars', desc: 'Vessel/voyage, B/L, Container, Shipper, Consignee, Port' },
  { id: 'attendance', label: '2. Attendance Register', desc: 'Surveyor, Consignee, CHA & Shipping Line representatives' },
  { id: 'narrative_circ', label: '3. Circumstances of Loss', desc: 'Voyage history, discharge, CFS transfer & instructions' },
  { id: 'narrative_survey', label: '4. Condition of Container & Cargo Findings', desc: 'Structural check, light/hose test & silver nitrate test' },
  { id: 'table', label: '5. Damage Inventory & Reconciliation Table', desc: 'Itemized damage counts by defect category' },
  { id: 'narrative_cause', label: '6. Cause of Loss & Liability', desc: 'Proximate causation analysis & carrier reservation' },
  { id: 'narrative_reserve', label: '7. Claim Reserve / Final Quantification', desc: 'Provisional reserve (PLA) or final loss calculation' },
  { id: 'photos', label: '8. Survey Photographs Plate', desc: 'Auto-numbered photo plate with container & damage views' },
  { id: 'enclosures', label: '9. Documentation & Enclosures', desc: 'Checklist of shipping documents, weighbridge slips & EIR' },
  { id: 'closure', label: '10. Formal Closure & Disclaimer', desc: 'Without prejudice disclaimer, date & signature block' },
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
  slate:  { bg: 'bg-slate-50',   border: 'border-slate-400',  text: 'text-slate-800',  badge: 'bg-slate-100 text-slate-700' },
  amber:  { bg: 'bg-amber-50',   border: 'border-amber-400',  text: 'text-amber-800',  badge: 'bg-amber-100 text-amber-700' },
  indigo: { bg: 'bg-indigo-50',  border: 'border-indigo-400', text: 'text-indigo-800', badge: 'bg-indigo-100 text-indigo-700' },
  teal:   { bg: 'bg-teal-50',    border: 'border-teal-400',   text: 'text-teal-800',   badge: 'bg-teal-100 text-teal-700' },
  yellow: { bg: 'bg-yellow-50',  border: 'border-yellow-400', text: 'text-yellow-800', badge: 'bg-yellow-100 text-yellow-700' },
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

  // General cargo section customization
  const [selectedSections, setSelectedSections] = useState<string[]>(
    GENERAL_CARGO_SECTIONS.map((s) => s.id)
  );
  const [showSectionOptions, setShowSectionOptions] = useState(false);

  // New report form state
  const [selectedTemplate, setSelectedTemplate] = useState('perishable-qc-sea');
  const [selectedMode, setSelectedMode] = useState<'SEA' | 'AIR'>('SEA');
  const [selectedFamily, setSelectedFamily] = useState('QC_REPORT');
  const [selectedState, setSelectedState] = useState<'PRELIMINARY' | 'FINAL'>('FINAL');
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
      const isGen = selectedTemplate.includes('general');
      const filtered = isGen
        ? data.filter((c) => c.category === 'GENERAL_CARGO')
        : data.filter((c) => c.category !== 'GENERAL_CARGO');
      if (filtered.length > 0) setSelectedCommodity(filtered[0].key);
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
      const nextIsGeneral = val.includes('general');
      const available = commodities.filter((c) =>
        nextIsGeneral ? c.category === 'GENERAL_CARGO' : c.category !== 'GENERAL_CARGO'
      );
      if (available.length > 0) {
        setSelectedCommodity(available[0].key);
      } else {
        setSelectedCommodity(nextIsGeneral ? 'STEEL_METALS' : 'APPLE');
      }
    }
  };

  const toggleSection = (secId: string) => {
    setSelectedSections((prev) =>
      prev.includes(secId) ? prev.filter((id) => id !== secId) : [...prev, secId]
    );
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setCreating(true);
      const isGeneral = selectedTemplate.includes('general');
      const newRep = await createReport({
        template_id: selectedTemplate,
        family: selectedFamily,
        mode: selectedMode,
        commodity: selectedCommodity,
        state: selectedFamily === 'SURVEY_REPORT' ? selectedState : 'FINAL',
        selected_sections: isGeneral ? selectedSections : undefined,
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
                    <div className="flex items-center gap-1.5">
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
                      {rep.state === 'PRELIMINARY' ? (
                        <span className="text-[11px] px-2 py-0.5 rounded-full font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                          PLA (Preliminary)
                        </span>
                      ) : rep.family === 'SURVEY_REPORT' ? (
                        <span className="text-[11px] px-2 py-0.5 rounded-full font-semibold bg-indigo-50 text-indigo-800 border border-indigo-200">
                          Final Survey
                        </span>
                      ) : (
                        <span className="text-[11px] px-2 py-0.5 rounded-full font-semibold bg-purple-50 text-purple-800 border border-purple-200">
                          QC Report
                        </span>
                      )}
                    </div>
                  </div>

                  <div>
                    <h3 className="font-semibold text-gray-900 text-base">
                      {rep.template_id.replace(/-/g, ' ').toUpperCase()}
                    </h3>
                    <p className="text-xs text-gray-500 mt-0.5">
                      Family: {rep.family} • Stage: {rep.state || 'FINAL'}
                    </p>
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

              {/* ── Survey Report Stage (Preliminary PLA vs Final) ───────── */}
              {selectedFamily === 'SURVEY_REPORT' && (
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1.5">
                    Survey Report Stage
                  </label>
                  <div className="grid grid-cols-2 gap-2.5">
                    <button
                      type="button"
                      onClick={() => setSelectedState('PRELIMINARY')}
                      className={`p-3 rounded-xl border text-left transition cursor-pointer ${
                        selectedState === 'PRELIMINARY'
                          ? 'border-blue-500 bg-blue-50/70 ring-2 ring-blue-400'
                          : 'border-gray-200 bg-white hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-xs text-gray-900">Preliminary (PLA)</span>
                        {selectedState === 'PRELIMINARY' && <CheckCircle2 className="w-4 h-4 text-blue-600 shrink-0" />}
                      </div>
                      <p className="text-[11px] text-gray-500 mt-1">
                        Issued promptly; preliminary findings, claim reserve &amp; reservation of rights
                      </p>
                    </button>

                    <button
                      type="button"
                      onClick={() => setSelectedState('FINAL')}
                      className={`p-3 rounded-xl border text-left transition cursor-pointer ${
                        selectedState === 'FINAL'
                          ? 'border-blue-500 bg-blue-50/70 ring-2 ring-blue-400'
                          : 'border-gray-200 bg-white hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-xs text-gray-900">Final Survey Report</span>
                        {selectedState === 'FINAL' && <CheckCircle2 className="w-4 h-4 text-blue-600 shrink-0" />}
                      </div>
                      <p className="text-[11px] text-gray-500 mt-1">
                        Complete causation analysis, itemized damages, &amp; final adjustment
                      </p>
                    </button>
                  </div>
                </div>
              )}

              {/* ── Commodity / Cargo Details ────────────────────────────── */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  {selectedTemplate.includes('general') ? 'General Cargo Subcategory' : 'Perishable Fruit Commodity & Defect Preset'}
                  <span className="ml-2 text-xs font-normal text-gray-400">
                    — mined from {commodities.reduce((s, c) => s + c.report_count, 0)} real client reports
                  </span>
                </label>

                {commoditiesLoading ? (
                  <div className="flex items-center gap-2 text-sm text-gray-500 py-4">
                    <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                    Loading cargo templates…
                  </div>
                ) : commodities.length === 0 ? (
                  <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3">
                    Corpus mining output not found. Run <code>tools/mine_corpus.py</code> to generate presets.
                  </div>
                ) : (
                  <>
                    {/* Grid of commodity / cargo cards */}
                    {(() => {
                      const isGeneral = selectedTemplate.includes('general');
                      const visibleCommodities = commodities.filter((c) =>
                        isGeneral ? c.category === 'GENERAL_CARGO' : c.category !== 'GENERAL_CARGO'
                      );

                      return (
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-56 overflow-y-auto pr-1">
                          {visibleCommodities.map((c) => {
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
                                className={`relative flex flex-col items-center gap-1 p-2.5 rounded-xl border-2 text-center transition cursor-pointer
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
                                  {c.report_count > 0 ? `${c.report_count} reports` : 'Template preset'}
                                </span>
                              </button>
                            );
                          })}
                        </div>
                      );
                    })()}

                    {/* Expanded detail panel for selected commodity / cargo */}
                    {selectedCommodityData && (
                      <div className="mt-3 bg-gray-50 border border-gray-200 rounded-xl p-4 space-y-3 text-xs">
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <p className="font-bold text-gray-800 text-sm">
                              {selectedCommodityData.emoji} {selectedCommodityData.display}
                              <span className="ml-2 font-normal text-gray-500">· unit: {selectedCommodityData.unit}</span>
                            </p>
                            {selectedCommodityData.description && (
                              <p className="text-gray-600 mt-0.5 font-medium">{selectedCommodityData.description}</p>
                            )}
                            <p className="text-gray-500 mt-0.5">
                              {selectedCommodityData.report_count > 0
                                ? `Based on ${selectedCommodityData.report_count} real client reports`
                                : 'Pre-configured canonical industry template'}
                            </p>
                          </div>
                          <Info className="w-4 h-4 text-gray-400 shrink-0 mt-0.5" />
                        </div>

                        {/* Defect columns */}
                        <div>
                          <p className="font-semibold text-gray-700 mb-1.5">Damage / Defect Columns (auto-prefilled):</p>
                          <div className="flex flex-wrap gap-1.5">
                            {selectedCommodityData.defect_columns.map((col) => (
                              <span key={col} className="bg-white border border-gray-300 text-gray-700 px-2 py-0.5 rounded-md font-mono text-[10px]">
                                {col}
                              </span>
                            ))}
                          </div>
                        </div>

                        {/* Top narrative clause preview */}
                        {selectedCommodityData.top_narrative_clauses && selectedCommodityData.top_narrative_clauses.length > 0 && (
                          <div>
                            <p className="font-semibold text-gray-700 mb-1">Common Corpus Wording (pre-filled):</p>
                            <p className="italic text-gray-600 leading-relaxed line-clamp-2">
                              "{selectedCommodityData.top_narrative_clauses[0]}"
                            </p>
                          </div>
                        )}
                      </div>
                    )}

                    {/* General Cargo Section Checklist */}
                    {selectedTemplate.includes('general') && (
                      <div className="mt-4 bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <SlidersHorizontal className="w-4 h-4 text-slate-700" />
                            <span className="font-bold text-xs text-slate-900">
                              Report Sections Included ({selectedSections.length} of {GENERAL_CARGO_SECTIONS.length})
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              onClick={() => setSelectedSections(GENERAL_CARGO_SECTIONS.map((s) => s.id))}
                              className="text-[11px] font-semibold text-blue-600 hover:text-blue-800 cursor-pointer"
                            >
                              Select All
                            </button>
                            <span className="text-gray-300">|</span>
                            <button
                              type="button"
                              onClick={() => setSelectedSections(['particulars', 'attendance', 'narrative_survey', 'table', 'photos'])}
                              className="text-[11px] font-semibold text-slate-600 hover:text-slate-800 cursor-pointer"
                            >
                              Essential Only
                            </button>
                          </div>
                        </div>

                        <p className="text-[11px] text-slate-500">
                          Customize which modules and sections appear in this General Cargo report.
                        </p>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                          {GENERAL_CARGO_SECTIONS.map((sec) => {
                            const checked = selectedSections.includes(sec.id);
                            return (
                              <div
                                key={sec.id}
                                onClick={() => toggleSection(sec.id)}
                                className={`flex items-start gap-2.5 p-2 rounded-lg border text-left cursor-pointer transition select-none ${
                                  checked
                                    ? 'bg-white border-blue-400 shadow-xs'
                                    : 'bg-slate-100/60 border-slate-200 text-gray-400'
                                }`}
                              >
                                <div className="mt-0.5 shrink-0">
                                  {checked ? (
                                    <CheckSquare className="w-4 h-4 text-blue-600" />
                                  ) : (
                                    <Square className="w-4 h-4 text-gray-300" />
                                  )}
                                </div>
                                <div className="min-w-0 flex-1">
                                  <div className={`font-bold text-xs leading-tight ${checked ? 'text-gray-800' : 'text-gray-500'}`}>
                                    {sec.label}
                                  </div>
                                  <div className="text-[10px] text-gray-500 truncate mt-0.5">
                                    {sec.desc}
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
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

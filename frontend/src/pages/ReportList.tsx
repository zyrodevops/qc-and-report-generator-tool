import React, { useState, useEffect } from 'react';
import { FileText, Plus, Ship, Plane, Calendar, ArrowRight, Loader2 } from 'lucide-react';
import { fetchReports, createReport, ReportSummary } from '../api/client';

interface ReportListProps {
  onSelectReport: (report: ReportSummary) => void;
}

export const ReportList: React.FC<ReportListProps> = ({ onSelectReport }) => {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [creating, setCreating] = useState(false);

  // New report form state
  const [selectedTemplate, setSelectedTemplate] = useState('perishable-qc-sea');
  const [selectedMode, setSelectedMode] = useState<'SEA' | 'AIR'>('SEA');
  const [selectedFamily, setSelectedFamily] = useState('QC_REPORT');
  const [year, setYear] = useState(2026);

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

  useEffect(() => {
    loadReports();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setCreating(true);
      const newRep = await createReport({
        template_id: selectedTemplate,
        family: selectedFamily,
        mode: selectedMode,
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

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap justify-between items-center gap-4 bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
        <div>
          <h1 className="text-2xl font-black text-gray-900 tracking-tight">Marine Cargo Survey Reports</h1>
          <p className="text-sm text-gray-500 mt-1">
            IRDAI-Licensed Marine Cargo Agencies — QC & Survey Report Platform
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
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
            Click &quot;Create New Report&quot; to initialize a new survey with automated gapless M-&lt;n&gt;-2026 numbering.
          </p>
          <button
            onClick={() => setShowModal(true)}
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

      {/* CREATE REPORT MODAL */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-6">
            <div className="flex justify-between items-center pb-3 border-b border-gray-100">
              <h2 className="text-xl font-bold text-gray-900">New Marine Cargo Survey Report</h2>
              <button
                onClick={() => setShowModal(false)}
                className="text-gray-400 hover:text-gray-600 text-2xl font-light leading-none"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">
                  Report Type & Product
                </label>
                <select
                  value={selectedTemplate}
                  onChange={(e) => {
                    const val = e.target.value;
                    setSelectedTemplate(val);
                    if (val.includes('qc')) setSelectedFamily('QC_REPORT');
                    else setSelectedFamily('SURVEY_REPORT');
                    if (val.includes('air')) setSelectedMode('AIR');
                    else setSelectedMode('SEA');
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                >
                  <option value="perishable-qc-sea">Perishable Cargo QC Report – Sea Shipment</option>
                  <option value="perishable-qc-air">Perishable Cargo QC Report – Air Shipment</option>
                  <option value="general-cargo-sea">General Cargo Survey – Sea Shipment</option>
                  <option value="general-cargo-air">General Cargo Survey – Air Shipment</option>
                  <option value="perishable-survey-sea">Perishable Cargo Survey – Sea Shipment</option>
                  <option value="perishable-survey-air">Perishable Cargo Survey – Air Shipment</option>
                </select>
              </div>

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

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-800">
                <p className="font-semibold">Sequential Number Allocation:</p>
                <p className="mt-0.5">
                  The server atomically issues consecutive <code className="font-mono">M-&lt;n&gt;-{year}</code> without gaps or duplicates under concurrency.
                </p>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-gray-100">
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
                  Allocate & Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};


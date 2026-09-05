import React, { useState } from 'react';
import {
  ArrowLeft,
  Download,
  Save,
  Ship,
  Plane,
  FileText,
  Clock,
  Layers,
  CheckCircle,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { ReportSummary, updateBlockState, getDownloadDocxUrl, getAuthHeaders } from '../api/client';
import { TableGrid } from '../components/tables/TableGrid';
import { PhotoTray } from '../components/photos/PhotoTray';

interface ReportFormProps {
  report: ReportSummary;
  onBack: () => void;
}

export const ReportForm: React.FC<ReportFormProps> = ({ report, onBack }) => {
  const [blockState, setBlockState] = useState<any>(report.block_state || {});
  const [saving, setSaving] = useState(false);
  const [savedMsg, setSavedMsg] = useState(false);
  const [csvModalBlockId, setCsvModalBlockId] = useState<string | null>(null);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);

  const mode = blockState?.transport?.mode || 'SEA';
  const blocks = blockState?.blocks || [];

  const handleBlockChange = (updatedBlock: any) => {
    const updated = blocks.map((b: any) => (b.id === updatedBlock.id ? updatedBlock : b));
    setBlockState({ ...blockState, blocks: updated });
    setSavedMsg(false);
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await updateBlockState(report.id, blockState);
      setSavedMsg(true);
      setTimeout(() => setSavedMsg(false), 3000);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDownloadDocx = () => {
    window.location.href = getDownloadDocxUrl(report.id);
  };

  const handleCsvImport = async (blockId: string) => {
    if (!csvFile) return;
    setImporting(true);
    try {
      const formData = new FormData();
      formData.append('file', csvFile);

      const res = await fetch(`/api/reports/${report.id}/import/spreadsheet`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: formData,
      });

      if (!res.ok) throw new Error('Spreadsheet parse failed');
      const data = await res.json();

      // Simple auto-mapping: match headers to categories
      const targetBlock = blocks.find((b: any) => b.id === blockId);
      if (targetBlock && data.sample_rows) {
        const catKeys = targetBlock.categories.map((c: any) => c.key);
        const mappedRows = data.sample_rows.map((sr: any, idx: number) => {
          const vals: Record<string, any> = {};
          catKeys.forEach((k: string) => {
            vals[k] = sr[k] || sr[k.toLowerCase()] || 0;
          });
          return {
            group: sr['group'] || sr['Sample'] || `Row ${idx + 1}`,
            values: vals,
          };
        });

        handleBlockChange({
          ...targetBlock,
          rows: mappedRows,
        });
      }
      setCsvModalBlockId(null);
      setCsvFile(null);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-16">
      {/* TOP ACTION BAR */}
      <div className="sticky top-4 z-40 bg-white/95 backdrop-blur-md p-4 rounded-xl border border-gray-200 shadow-sm flex flex-wrap justify-between items-center gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-2 hover:bg-gray-100 rounded-lg text-gray-600 transition"
            title="Back to Reports list"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-mono font-bold text-xl text-blue-900 tracking-wide">
                {report.report_number}
              </h2>
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
              <span className="text-xs bg-gray-100 text-gray-700 font-semibold px-2 py-0.5 rounded">
                {report.state}
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-0.5">
              Template: {report.template_id} • All totals recomputed on render
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {savedMsg && (
            <span className="flex items-center gap-1 text-xs font-semibold text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded border border-emerald-200 animate-fade-in">
              <CheckCircle className="w-4 h-4" /> State Saved
            </span>
          )}

          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-1.5 bg-gray-100 hover:bg-gray-200 text-gray-800 font-semibold text-sm px-4 py-2 rounded-lg transition"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Save Draft
          </button>

          <button
            type="button"
            onClick={handleDownloadDocx}
            className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm px-5 py-2 rounded-lg shadow-sm transition"
          >
            <Download className="w-4 h-4" />
            Generate & Download DOCX
          </button>
        </div>
      </div>

      {/* TRANSPORT METADATA CARD */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4">
        <div className="flex items-center gap-2 pb-2 border-b border-gray-100 font-bold text-gray-800">
          <Layers className="w-5 h-5 text-blue-600" />
          <span>Shipment Transport Details ({mode})</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div>
            <label className="block text-xs font-semibold text-gray-500 mb-1">
              Transport Document ({mode === 'AIR' ? 'Air Waybill' : 'Bill of Lading'})
            </label>
            <input
              type="text"
              value={blockState?.transport?.document?.number || ''}
              onChange={(e) =>
                setBlockState({
                  ...blockState,
                  transport: {
                    ...blockState.transport,
                    document: { ...blockState.transport?.document, number: e.target.value },
                  },
                })
              }
              className="w-full px-3 py-1.5 border border-gray-300 rounded font-mono text-sm outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-500 mb-1">
              Carriage Unit ({mode === 'AIR' ? 'ULD / Pallet' : 'Container Number'})
            </label>
            <input
              type="text"
              value={blockState?.carriage_units?.[0]?.identifier || ''}
              onChange={(e) => {
                const units = [...(blockState.carriage_units || [{ id: 'u1' }])];
                units[0] = { ...units[0], identifier: e.target.value };
                setBlockState({ ...blockState, carriage_units: units });
              }}
              className="w-full px-3 py-1.5 border border-gray-300 rounded font-mono text-sm outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-500 mb-1">Gross Cargo Weight (kg)</label>
            <input
              type="text"
              value={blockState?.weights?.gross_kg || ''}
              onChange={(e) =>
                setBlockState({
                  ...blockState,
                  weights: { ...blockState.weights, gross_kg: e.target.value },
                })
              }
              className="w-full px-3 py-1.5 border border-gray-300 rounded font-mono text-sm outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      {/* GENERATED BLOCKS LIST */}
      <div className="space-y-6">
        {blocks.map((block: any) => {
          if (block.type === 'particulars') {
            return (
              <div key={block.id} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4">
                <div className="flex items-center gap-2 pb-2 border-b border-gray-100 font-bold text-gray-800">
                  <FileText className="w-5 h-5 text-blue-600" />
                  <span>Particulars of Survey</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {block.rows.map((row: any, rIdx: number) => (
                    <div key={rIdx}>
                      <label className="block text-xs font-semibold text-gray-500 mb-1">{row.label}</label>
                      <input
                        type="text"
                        value={Array.isArray(row.value) ? row.value.join(', ') : row.value}
                        onChange={(e) => {
                          const newRows = [...block.rows];
                          newRows[rIdx] = { ...newRows[rIdx], value: [e.target.value] };
                          handleBlockChange({ ...block, rows: newRows });
                        }}
                        className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm outline-none focus:ring-1 focus:ring-blue-500"
                      />
                    </div>
                  ))}
                </div>
              </div>
            );
          }

          if (block.type === 'narrative') {
            return (
              <div key={block.id} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-3">
                <div className="flex items-center gap-2 pb-2 border-b border-gray-100 font-bold text-gray-800">
                  <Clock className="w-5 h-5 text-blue-600" />
                  <span>{block.section || 'Narrative Circumstances'}</span>
                </div>
                <textarea
                  rows={3}
                  value={block.additional_text || ''}
                  onChange={(e) => handleBlockChange({ ...block, additional_text: e.target.value })}
                  placeholder="Enter survey findings and circumstances..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            );
          }

          if (block.type === 'measurements') {
            return (
              <div key={block.id} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4">
                <div className="flex items-center gap-2 pb-2 border-b border-gray-100 font-bold text-gray-800">
                  <Clock className="w-5 h-5 text-emerald-600" />
                  <span>On-Site Measurements</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-gray-50 text-xs text-gray-500 uppercase border-b">
                        <th className="py-2 px-3 text-left">Subject</th>
                        <th className="py-2 px-3 text-left">Method</th>
                        <th className="py-2 px-3 text-left">Min / Value</th>
                        <th className="py-2 px-3 text-left">Max</th>
                        <th className="py-2 px-3 text-left">Unit</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {block.rows.map((row: any, rIdx: number) => (
                        <tr key={rIdx}>
                          <td className="py-2 px-3 font-semibold text-gray-800">{row.subject}</td>
                          <td className="py-2 px-3 text-gray-600">{row.method}</td>
                          <td className="py-2 px-3">
                            <input
                              type="text"
                              value={row.min || row.value || ''}
                              onChange={(e) => {
                                const newRows = [...block.rows];
                                newRows[rIdx] = { ...newRows[rIdx], min: e.target.value };
                                handleBlockChange({ ...block, rows: newRows });
                              }}
                              className="w-20 px-2 py-1 border rounded text-sm text-right font-mono"
                            />
                          </td>
                          <td className="py-2 px-3">
                            <input
                              type="text"
                              value={row.max || ''}
                              onChange={(e) => {
                                const newRows = [...block.rows];
                                newRows[rIdx] = { ...newRows[rIdx], max: e.target.value };
                                handleBlockChange({ ...block, rows: newRows });
                              }}
                              className="w-20 px-2 py-1 border rounded text-sm text-right font-mono"
                            />
                          </td>
                          <td className="py-2 px-3 font-semibold text-gray-700">{row.unit}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            );
          }

          if (block.type === 'table') {
            return (
              <TableGrid
                key={block.id}
                block={block}
                onChange={handleBlockChange}
                onImportCsv={() => setCsvModalBlockId(block.id)}
              />
            );
          }

          if (block.type === 'photo_plate') {
            return (
              <PhotoTray
                key={block.id}
                block={block}
                reportId={report.id}
                onChange={handleBlockChange}
              />
            );
          }

          if (block.type === 'fixed_text') {
            return (
              <div key={block.id} className="bg-gray-50 rounded-xl border border-gray-200 p-5 text-xs text-gray-600 space-y-1">
                <span className="font-bold text-gray-700 uppercase">Document Legal Text:</span>
                <p className="italic">{block.content}</p>
              </div>
            );
          }

          return null;
        })}
      </div>

      {/* SPREADSHEET IMPORT MODAL */}
      {csvModalBlockId && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="font-bold text-gray-900 text-lg">Import Spreadsheet / CSV</h3>
            <p className="text-xs text-gray-500">
              Select an .xlsx or .csv tally sheet. Live <code className="font-mono">=SUM()</code> formulas are read as computed values per Master Spec §10.4.
            </p>

            <input
              type="file"
              accept=".csv, .xlsx, .xls"
              onChange={(e) => setCsvFile(e.target.files?.[0] || null)}
              className="w-full text-sm file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />

            <div className="flex justify-end gap-2 pt-3 border-t">
              <button
                type="button"
                onClick={() => setCsvModalBlockId(null)}
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!csvFile || importing}
                onClick={() => handleCsvImport(csvModalBlockId)}
                className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-semibold disabled:opacity-50"
              >
                {importing && <Loader2 className="w-4 h-4 animate-spin" />}
                Import Data
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};


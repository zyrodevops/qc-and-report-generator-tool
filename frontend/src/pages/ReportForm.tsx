import React, { useMemo, useState } from 'react';
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
  Eye,
  Edit3,
} from 'lucide-react';
import { ReportSummary, patchBlockState, getDownloadDocxUrl } from '../api/client';
import { TableGrid } from '../components/tables/TableGrid';
import { SectionToggle, isIncluded } from '../components/SectionToggle';
import { PhotoTray } from '../components/photos/PhotoTray';
import { ReportPreview } from '../components/preview/ReportPreview';
import { NarrativeBlock } from '../components/preview/blocks/NarrativeBlock';
import { clauseContextFrom, findBlanks } from '../utils/clauseContext';

interface ReportFormProps {
  report: ReportSummary;
  onBack: () => void;
}

export const ReportForm: React.FC<ReportFormProps> = ({ report, onBack }) => {
  const [activeTab, setActiveTab] = useState<'edit' | 'preview'>('edit');
  const [blockState, setBlockState] = useState<any>(report.block_state || {});
  const [saving, setSaving] = useState(false);
  const [savedMsg, setSavedMsg] = useState(false);
  // True while there are edits the server has not got yet.
  const [dirty, setDirty] = useState(false);

  const [version, setVersion] = useState<number>(report.version || 1);
  const [conflictMsg, setConflictMsg] = useState<string | null>(null);

  const mode = blockState?.transport?.mode || 'SEA';
  const blocks = blockState?.blocks || [];

  const handleBlockChange = (updatedBlock: any) => {
    setBlockState((prev: any) => {
      const currentBlocks = prev?.blocks || [];
      const updated = currentBlocks.map((b: any) => (b.id === updatedBlock.id ? updatedBlock : b));
      return { ...prev, blocks: updated };
    });
    setDirty(true);
    setSavedMsg(false);
    setConflictMsg(null);
  };

  const handlePhotoBlockUpdate = (updatedBlock: any, updatedAssets?: Record<string, any>) => {
    setBlockState((prev: any) => {
      const currentBlocks = prev?.blocks || [];
      const updated = currentBlocks.map((b: any) => (b.id === updatedBlock.id ? updatedBlock : b));
      return {
        ...prev,
        blocks: updated,
        assets: updatedAssets ? { ...(prev?.assets || {}), ...updatedAssets } : prev?.assets,
      };
    });
    setDirty(true);
    setSavedMsg(false);
    setConflictMsg(null);
  };

  /** Returns true when the server now holds exactly what is on screen. */
  const handleSave = async (): Promise<boolean> => {
    try {
      setSaving(true);
      setConflictMsg(null);
      const res = await patchBlockState(report.id, blockState, version);
      setVersion(res.new_version);
      setDirty(false);
      setSavedMsg(true);
      setTimeout(() => setSavedMsg(false), 3000);
      return true;
    } catch (err: any) {
      if (err.name === 'VersionConflictError') {
        setConflictMsg(err.message);
      } else {
        alert(err.message);
      }
      return false;
    } finally {
      setSaving(false);
    }
  };

  /**
   * Downloads are built from the server's copy, so unsaved edits are saved
   * first. Without this a surveyor who corrected a figure and pressed Download
   * got the report as it was before his correction.
   */
  const saveIfNeeded = async (): Promise<boolean> => (dirty ? handleSave() : true);

  // For the clause pickers: the report as it stands on screen, saved or not.
  const clauseContext = useMemo(() => clauseContextFrom(blockState), [blockState]);

  /**
   * Before a download: blanks left in the report ([DATE], [NAME], a starting
   * placeholder like [Shipper Name, Country]) would print as they are. The
   * surveyor is told where they are and chooses; nothing is filled for him.
   */
  const beforeDownload = async (): Promise<boolean> => {
    const left = findBlanks(blockState);
    if (left.length) {
      const lines = left.slice(0, 12).map((l) => `• ${l.where}: ${l.blanks.join(' ')}`);
      const more = left.length > 12 ? `\n…and ${left.length - 12} more` : '';
      const ok = window.confirm(
        `These blanks are still in the report and will print as they are:\n\n${lines.join('\n')}${more}\n\nDownload anyway?`,
      );
      if (!ok) return false;
    }
    return saveIfNeeded();
  };

  const handleDownloadDocx = async () => {
    if (await beforeDownload()) window.location.href = getDownloadDocxUrl(report.id);
  };

  /** The workbench saved on the server: take its state and its new version. */
  const handleWorkbenchSaved = (updatedBlockState: any, newVersion: number) => {
    setBlockState(updatedBlockState);
    if (newVersion) setVersion(newVersion);
    setDirty(false);
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

        {/* VIEW TABS */}
        <div className="flex items-center bg-gray-100 p-1 rounded-lg border border-gray-200">
          <button
            type="button"
            onClick={() => setActiveTab('edit')}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md transition ${
              activeTab === 'edit'
                ? 'bg-white text-blue-900 shadow-xs'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <Edit3 className="w-3.5 h-3.5" />
            Form Editor
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('preview')}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md transition ${
              activeTab === 'preview'
                ? 'bg-white text-blue-900 shadow-xs'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <Eye className="w-3.5 h-3.5" />
            A4 HTML Preview
          </button>
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

      {conflictMsg && (
        <div className="bg-amber-50 border border-amber-200 text-amber-900 px-4 py-3 rounded-lg flex items-center gap-2 text-sm shadow-xs animate-fade-in">
          <AlertCircle className="w-5 h-5 text-amber-600 shrink-0" />
          <div>
            <p className="font-semibold">Version Conflict Detected (HTTP 409)</p>
            <p className="text-xs text-amber-700 mt-0.5">{conflictMsg}</p>
          </div>
        </div>
      )}

      {activeTab === 'preview' ? (
        <ReportPreview
          report={report}
          blockState={blockState}
          reportNumber={report.report_number}
          onBackToEdit={() => setActiveTab('edit')}
          onBlockChange={handleBlockChange}
          onBlockStateChange={setBlockState}
          editable={true}
          beforeDownload={beforeDownload}
        />
      ) : (
        <>
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
            const included = isIncluded(block.included);
            return (
              <div
                key={block.id}
                className={`relative rounded-xl shadow-sm border p-5 ${
                  included ? 'bg-white border-gray-200' : 'bg-gray-50 border-dashed border-gray-300'
                }`}
              >
                {/* Tick box in the corner: untick to leave this section out of
                    the report. The text is kept and comes back when re-ticked. */}
                <div className="absolute top-3 right-4 z-10">
                  <SectionToggle
                    checked={included}
                    onChange={(next) => handleBlockChange({ ...block, included: next })}
                  />
                </div>

                {included ? (
                  <NarrativeBlock
                    block={block}
                    onChange={handleBlockChange}
                    editable={true}
                    clauseContext={clauseContext}
                  />
                ) : (
                  <div className="pr-28">
                    <div className="text-sm font-bold text-gray-400 uppercase tracking-wide line-through">
                      {block.section || block.title || 'Section'}
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      Left out of the report. What you wrote is kept — tick the box to put it back.
                    </p>
                  </div>
                )}
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
                        <th className="py-2 px-3 text-left w-24">In report</th>
                        <th className="py-2 px-3 text-left">Subject</th>
                        <th className="py-2 px-3 text-left">Method</th>
                        <th className="py-2 px-3 text-left">Min / Value</th>
                        <th className="py-2 px-3 text-left">Max</th>
                        <th className="py-2 px-3 text-left">Unit</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {block.rows.map((row: any, rIdx: number) => (
                        <tr key={rIdx} className={isIncluded(row.included) ? '' : 'opacity-40'}>
                          <td className="py-2 px-3">
                            <SectionToggle
                              compact
                              label=""
                              checked={isIncluded(row.included)}
                              onChange={(next) => {
                                const newRows = [...block.rows];
                                newRows[rIdx] = { ...newRows[rIdx], included: next };
                                handleBlockChange({ ...block, rows: newRows });
                              }}
                            />
                          </td>
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
            // No fallback commodity here. Guessing one would hand the surveyor
            // another fruit's defect columns, and he would have to notice that
            // the grid is wrong before he starts typing counts into it.
            const tableCommodity = blockState?.metadata?.commodity as string | undefined;
            return (
              <TableGrid
                key={block.id}
                block={block}
                reportId={report.id}
                commodity={tableCommodity}
                onChange={handleBlockChange}
                onSaved={handleWorkbenchSaved}
                onApply={handleSave}
                dirty={dirty}
                applying={saving}
              />
            );
          }

          if (block.type === 'photo_plate') {
            return (
              <PhotoTray
                key={block.id}
                block={block}
                reportId={report.id}
                assets={blockState?.assets || {}}
                onChange={handleBlockChange}
                onUpdateBlockAndAssets={handlePhotoBlockUpdate}
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
      </>
      )}

    </div>
  );
};


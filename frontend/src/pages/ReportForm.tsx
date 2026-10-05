import React, { useEffect, useMemo, useState } from 'react';
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
  Plus,
  Trash2,
} from 'lucide-react';
import { ReportSummary, patchBlockState, getDownloadDocxUrl } from '../api/client';
import { TableGrid } from '../components/tables/TableGrid';
import { AddFruitTable } from '../components/tables/AddFruitTable';
import { SectionToggle, isIncluded } from '../components/SectionToggle';
import { PhotoTray } from '../components/photos/PhotoTray';
import { ReportPreview } from '../components/preview/ReportPreview';
import { NarrativeBlock } from '../components/preview/blocks/NarrativeBlock';
import { RecordersBlock } from '../components/preview/blocks/RecordersBlock';
import { clauseContextFrom, fillNamedBlanks, findBlanks, generalCargoValues } from '../utils/clauseContext';
import { normalizeVoyageAsync } from '../utils/portNormalizer';
import { ShipmentDocuments } from '../components/documents/ShipmentDocuments';
import { CoverEditor } from '../components/generalCargo/CoverEditor';
import { LossTypePicker } from '../components/generalCargo/LossTypePicker';
import { AttendanceEditor } from '../components/generalCargo/AttendanceEditor';
import { SurveyUnitCard } from '../components/generalCargo/SurveyUnitCard';
import { isGeneralCargo, newSurveyUnit, paragraphHeadings, withReportTables } from '../utils/generalCargo';
import { ReportTableEditor } from '../components/generalCargo/ReportTableEditor';

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
      let updated = currentBlocks.map((b: any) => (b.id === updatedBlock.id ? updatedBlock : b));
      // If Cause of Loss condition changed, sync temperature_recorders block inclusion
      if (
        (updatedBlock.id === 'b_cause' || /cause of loss/i.test(updatedBlock.section || '')) &&
        updatedBlock.cause_condition
      ) {
        if (updatedBlock.cause_condition === 'no_recorder_data') {
          updated = updated.map((b: any) => (b.type === 'temperature_recorders' ? { ...b, included: false } : b));
        } else if (
          updatedBlock.cause_condition === 'carrier_breach' ||
          updatedBlock.cause_condition === 'cold_chain_complied'
        ) {
          updated = updated.map((b: any) =>
            b.type === 'temperature_recorders' && (b.recorders || []).length > 0 ? { ...b, included: true } : b
          );
        }
      }
      return { ...prev, blocks: updated };
    });
    setDirty(true);
    setSavedMsg(false);
    setConflictMsg(null);
  };

  // One condition-found table per fruit in the cargo.
  const tableBlocks = blocks.filter((b: any) => b.type === 'table');
  const shipmentContainers: string[] = (blockState?.metadata?.shipment?.containers || [])
    .map((c: any) => c?.container)
    .filter(Boolean);

  const addTableAfter = (afterId: string, newBlock: any) => {
    setBlockState((prev: any) => {
      const list = [...(prev?.blocks || [])];
      const at = list.findIndex((b: any) => b.id === afterId);
      list.splice(at < 0 ? list.length : at + 1, 0, newBlock);
      return { ...prev, blocks: list };
    });
    setDirty(true);
    setSavedMsg(false);
  };

  const removeTable = (block: any) => {
    const filled = (block.rows || []).length;
    if (
      filled > 0 &&
      !window.confirm(`Remove the table "${block.title || 'Condition found'}"? Its ${filled} row${filled > 1 ? 's' : ''} will be deleted.`)
    ) {
      return;
    }
    setBlockState((prev: any) => ({
      ...prev,
      blocks: (prev?.blocks || []).filter((b: any) => b.id !== block.id),
    }));
    setDirty(true);
    setSavedMsg(false);
  };

  // ---- general cargo: the OUR SURVEY paragraphs (one per container or visit)
  const gc = isGeneralCargo(blockState);
  const headings = useMemo(() => paragraphHeadings(blockState), [blockState]);
  const surveyUnits = blocks.filter((b: any) => b.type === 'survey_unit');
  const editBlocks = (fn: (list: any[]) => any[]) => {
    setBlockState((prev: any) => ({ ...prev, blocks: fn([...(prev?.blocks || [])]) }));
    setDirty(true);
    setSavedMsg(false);
  };
  const addSurveyAfter = (afterId: string, init: Record<string, string> = {}) =>
    editBlocks((list) => {
      const at = list.findIndex((b: any) => b.id === afterId);
      list.splice(at < 0 ? list.length : at + 1, 0, newSurveyUnit(list, init));
      return list;
    });
  const removeSurvey = (block: any) => {
    const written = String(block.additional_text || '').trim();
    if (written && !window.confirm('Remove this survey paragraph? Its text will be deleted.')) return;
    editBlocks((list) => list.filter((b: any) => b.id !== block.id));
  };
  const moveSurvey = (block: any, dir: -1 | 1) =>
    editBlocks((list) => {
      const units = list.map((b: any, i: number) => ({ b, i })).filter((x) => x.b.type === 'survey_unit');
      const k = units.findIndex((x) => x.b.id === block.id);
      const other = units[k + dir];
      if (!other) return list;
      const a = units[k].i;
      [list[a], list[other.i]] = [list[other.i], list[a]];
      return list;
    });
  // One survey paragraph for each container on the documents that has none yet.
  const containersWithoutSurvey = shipmentContainers.filter(
    (c) => !surveyUnits.some((u: any) => String(u.container || '').toUpperCase() === c.toUpperCase()),
  );
  const addSurveyPerContainer = () =>
    editBlocks((list) => {
      let last = list.map((b: any) => b.type).lastIndexOf('survey_unit');
      // An untouched first paragraph takes the first container instead of staying empty.
      const firstIdx = list.findIndex((b: any) => b.type === 'survey_unit');
      const todo = [...containersWithoutSurvey];
      if (firstIdx >= 0) {
        const f = list[firstIdx];
        if (!f.container && !String(f.additional_text || '').trim() && todo.length) {
          list[firstIdx] = { ...f, container: todo.shift() };
        }
      }
      for (const c of todo) {
        const unit = newSurveyUnit(list, { container: c });
        list.splice(last + 1, 0, unit);
        last += 1;
      }
      return list;
    });

  const handlePhotoBlockUpdate =(updatedBlock: any, updatedAssets?: Record<string, any>) => {
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

  // General cargo: a report made before the report tables existed gets them (off).
  useEffect(() => {
    const next = withReportTables(blockState);
    if (next) setBlockState(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const coverFacts = useMemo(() => generalCargoValues(blockState?.blocks || []), [blockState]);
  const coverSeals: string[] = useMemo(() => {
    const row = ((blockState?.blocks || []).find((b: any) => b.type === 'particulars')?.rows || [])
      .find((r: any) => /seal/i.test(String(r.label || '')));
    const v = String(Array.isArray(row?.value) ? row.value[0] ?? '' : row?.value ?? '');
    return v.startsWith('[') ? [] : v.split(/[,&/]|\band\b/).map((x) => x.trim()).filter(Boolean);
  }, [blockState]);

  // General cargo: a named blank in wording already added ([VESSEL] …) is
  // filled as soon as the report has the value.
  useEffect(() => {
    const next = fillNamedBlanks(blockState);
    if (next) {
      setBlockState(next);
      setDirty(true);
    }
  }, [blockState]);

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
          {/* SHIPMENT DOCUMENTS: read the B/L, invoice, packing lists and recorders */}
          <ShipmentDocuments reportId={report.id} blockState={blockState} onApplied={handleWorkbenchSaved} />

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
          if (block.type === 'particulars' && gc) {
            return (
              <React.Fragment key={block.id}>
                <LossTypePicker
                  value={blockState?.metadata?.loss_types || []}
                  onChange={(next) => {
                    setBlockState((prev: any) => ({ ...prev, metadata: { ...prev?.metadata, loss_types: next } }));
                    setDirty(true);
                  }}
                />
                <CoverEditor block={block} onChange={handleBlockChange} />
              </React.Fragment>
            );
          }

          if (block.type === 'gc_table') {
            return (
              <ReportTableEditor
                key={block.id}
                block={block}
                onChange={handleBlockChange}
                containers={coverFacts.container_nos || []}
                seals={coverSeals}
              />
            );
          }

          if (block.type === 'attendance') {
            return (
              <div key={block.id} className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
                <AttendanceEditor
                  rows={block.rows || []}
                  intro={block.intro ?? ''}
                  label="Attendance (printed under Application)"
                  onChange={(rows, intro) => handleBlockChange({ ...block, rows, intro })}
                />
              </div>
            );
          }

          if (block.type === 'survey_unit') {
            const isLast = block.id === surveyUnits[surveyUnits.length - 1]?.id;
            return (
              <React.Fragment key={block.id}>
                <SurveyUnitCard
                  block={block}
                  heading={headings[block.id] || 'OUR SURVEY'}
                  onChange={handleBlockChange}
                  onRemove={surveyUnits.length > 1 ? () => removeSurvey(block) : undefined}
                  onMove={surveyUnits.length > 1 ? (dir) => moveSurvey(block, dir) : undefined}
                  containers={shipmentContainers}
                  clauseContext={clauseContext}
                  shipmentContainers={blockState?.metadata?.shipment?.containers || []}
                />
                {isLast && (
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => addSurveyAfter(block.id, { survey_date: block.survey_date || '', place: block.place || '' })}
                      className="flex-1 min-w-[16rem] text-sm text-blue-700 font-medium py-2.5 rounded-xl border border-dashed border-blue-300 bg-blue-50/40 hover:bg-blue-50"
                    >
                      + Add another survey paragraph (next container or visit)
                    </button>
                    {containersWithoutSurvey.length > 0 && (
                      <button
                        type="button"
                        onClick={addSurveyPerContainer}
                        className="flex-1 min-w-[16rem] text-sm text-emerald-700 font-medium py-2.5 rounded-xl border border-dashed border-emerald-300 bg-emerald-50/40 hover:bg-emerald-50"
                      >
                        + One paragraph per container from the documents ({containersWithoutSurvey.length} to add)
                      </button>
                    )}
                  </div>
                )}
              </React.Fragment>
            );
          }

          if (block.type === 'particulars') {
            return (
              <div key={block.id} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4">
                <div className="flex items-center gap-2 pb-2 border-b border-gray-100 font-bold text-gray-800">
                  <FileText className="w-5 h-5 text-blue-600" />
                  <span>Particulars of Survey</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {block.rows.map((row: any, rIdx: number) => {
                    const label = row.label || '';
                    const isTable =
                      row.type === 'table' ||
                      Boolean(row.headers) ||
                      (label.toLowerCase().includes('consignment') && (Boolean(row.rows) || Boolean(row.items)));

                    if (isTable) {
                      const headers = row.headers || ['Commodity / Variety', 'Count / Size', 'Total Boxes'];
                      const subItems: any[] = row.rows || row.items || [];
                      const footer = row.footer || '';

                      const updateSubItem = (sIdx: number, key: string, val: string) => {
                        const newRows = [...block.rows];
                        const items = [...(newRows[rIdx].rows || newRows[rIdx].items || [])];
                        items[sIdx] = { ...items[sIdx], [key]: val };
                        newRows[rIdx] = { ...newRows[rIdx], rows: items };
                        handleBlockChange({ ...block, rows: newRows });
                      };

                      const addSubItem = () => {
                        const newRows = [...block.rows];
                        const items = [...(newRows[rIdx].rows || newRows[rIdx].items || [])];
                        items.push({ col1: '', col2: '', col3: '' });
                        newRows[rIdx] = { ...newRows[rIdx], rows: items };
                        handleBlockChange({ ...block, rows: newRows });
                      };

                      const removeSubItem = (sIdx: number) => {
                        const newRows = [...block.rows];
                        const items = [...(newRows[rIdx].rows || newRows[rIdx].items || [])];
                        items.splice(sIdx, 1);
                        newRows[rIdx] = { ...newRows[rIdx], rows: items };
                        handleBlockChange({ ...block, rows: newRows });
                      };

                      const updateFooter = (val: string) => {
                        const newRows = [...block.rows];
                        newRows[rIdx] = { ...newRows[rIdx], footer: val, value: [val] };
                        handleBlockChange({ ...block, rows: newRows });
                      };

                      const autoSum = () => {
                        let total = 0;
                        for (const it of subItems) {
                          const bx = (it.col3 ?? it.boxes ?? it.cartons ?? it.total_boxes ?? '').toString().replace(/,/g, '').trim();
                          const n = parseInt(bx, 10);
                          if (!isNaN(n)) total += n;
                        }
                        updateFooter(`Total: ${total.toLocaleString()} boxes`);
                      };

                      return (
                        <div key={rIdx} className="md:col-span-2 bg-slate-50 p-4 rounded-lg border border-slate-200 space-y-3">
                          <div className="flex items-center justify-between">
                            <label className="text-xs font-bold uppercase tracking-wider text-slate-700">{label}</label>
                            <button
                              type="button"
                              onClick={autoSum}
                              className="text-xs text-blue-600 hover:text-blue-800 font-medium cursor-pointer"
                            >
                              Auto-calculate total
                            </button>
                          </div>
                          <div className="overflow-x-auto border border-slate-300 rounded bg-white">
                            <table className="w-full text-xs">
                              <thead className="bg-slate-100 border-b border-slate-300 text-slate-700">
                                <tr>
                                  <th className="p-2 text-left font-semibold">{headers[0]}</th>
                                  <th className="p-2 text-center font-semibold">{headers[1]}</th>
                                  <th className="p-2 text-right font-semibold">{headers[2]}</th>
                                  <th className="p-2 w-10"></th>
                                </tr>
                              </thead>
                              <tbody>
                                {subItems.map((item: any, sIdx: number) => {
                                  const col1 = item.col1 ?? item.variety ?? item.description ?? '';
                                  const col2 = item.col2 ?? item.count ?? item.size ?? item.count_size ?? '';
                                  const col3 = item.col3 ?? item.boxes ?? item.cartons ?? item.total_boxes ?? '';
                                  return (
                                    <tr key={sIdx} className="border-b border-slate-200">
                                      <td className="p-1">
                                        <input
                                          type="text"
                                          value={col1}
                                          onChange={(e) => updateSubItem(sIdx, 'col1', e.target.value)}
                                          placeholder="e.g. Royal Gala / Tenroy"
                                          className="w-full px-2 py-1 border border-slate-200 rounded text-xs"
                                        />
                                      </td>
                                      <td className="p-1">
                                        <input
                                          type="text"
                                          value={col2}
                                          onChange={(e) => updateSubItem(sIdx, 'col2', e.target.value)}
                                          placeholder="e.g. 180"
                                          className="w-full px-2 py-1 border border-slate-200 rounded text-xs text-center"
                                        />
                                      </td>
                                      <td className="p-1">
                                        <input
                                          type="text"
                                          value={col3}
                                          onChange={(e) => updateSubItem(sIdx, 'col3', e.target.value)}
                                          placeholder="e.g. 1,176"
                                          className="w-full px-2 py-1 border border-slate-200 rounded text-xs text-right"
                                        />
                                      </td>
                                      <td className="p-1 text-center">
                                        <button
                                          type="button"
                                          onClick={() => removeSubItem(sIdx)}
                                          className="text-red-500 hover:text-red-700 p-1 cursor-pointer"
                                          title="Remove row"
                                        >
                                          <Trash2 className="w-3.5 h-3.5" />
                                        </button>
                                      </td>
                                    </tr>
                                  );
                                })}
                              </tbody>
                            </table>
                          </div>
                          <div className="flex items-center justify-between gap-4 pt-1">
                            <button
                              type="button"
                              onClick={addSubItem}
                              className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 font-medium py-1 px-2 border border-blue-200 rounded bg-blue-50/50 hover:bg-blue-50 cursor-pointer"
                            >
                              <Plus className="w-3.5 h-3.5" /> Add Variety / Count
                            </button>
                            <div className="flex items-center gap-2 flex-1 max-w-md">
                              <span className="text-xs font-semibold text-slate-500 whitespace-nowrap">Footer Summary:</span>
                              <input
                                type="text"
                                value={footer}
                                onChange={(e) => updateFooter(e.target.value)}
                                placeholder="Total: X boxes (Gross Weight: ...)"
                                className="w-full px-2 py-1 border border-slate-300 rounded text-xs font-medium"
                              />
                            </div>
                          </div>
                        </div>
                      );
                    }

                    const isLong =
                      label.toLowerCase().includes('packing') ||
                      label.toLowerCase().includes('nature') ||
                      label.toLowerCase().includes('shipper') ||
                      label.toLowerCase().includes('consignee');

                    return (
                      <div key={rIdx} className={isLong ? 'md:col-span-2' : ''}>
                        <label className="block text-xs font-semibold text-gray-500 mb-1">{row.label}</label>
                        {isLong ? (
                          <textarea
                            rows={label.toLowerCase().includes('packing') ? 4 : 2}
                            value={Array.isArray(row.value) ? row.value.join('\n') : row.value}
                            onChange={(e) => {
                              const newRows = [...block.rows];
                              newRows[rIdx] = { ...newRows[rIdx], value: [e.target.value] };
                              handleBlockChange({ ...block, rows: newRows });
                            }}
                            className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm outline-none focus:ring-1 focus:ring-blue-500 font-sans"
                          />
                        ) : (
                          <input
                            type="text"
                            value={Array.isArray(row.value) ? row.value.join(', ') : row.value}
                            onChange={(e) => {
                              const newRows = [...block.rows];
                              newRows[rIdx] = { ...newRows[rIdx], value: [e.target.value] };
                              handleBlockChange({ ...block, rows: newRows });
                            }}
                            onBlur={async (e) => {
                              if (/voyage/i.test(label)) {
                                const val = e.target.value;
                                const normalized = await normalizeVoyageAsync(val);
                                if (normalized && normalized !== val) {
                                  const newRows = [...block.rows];
                                  newRows[rIdx] = { ...newRows[rIdx], value: [normalized] };
                                  handleBlockChange({ ...block, rows: newRows });
                                }
                              }
                            }}
                            className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm outline-none focus:ring-1 focus:ring-blue-500"
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          }

          if (block.type === 'narrative') {
            const included = isIncluded(block.included);
            const isCauseOfLoss =
              block.id === 'b_cause' ||
              block.section === 'cause_of_loss' ||
              /cause of loss/i.test(block.section || headings[block.id] || '');
            const recordersBlock = isCauseOfLoss ? blocks.find((b: any) => b.type === 'temperature_recorders') : undefined;

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
                    heading={headings[block.id]}
                    isFormEditor={true}
                    recordersBlock={recordersBlock}
                    onRecordersChange={handleBlockChange}
                    reportId={report.id}
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

          if (block.type === 'temperature_recorders') {
            // When Paragraph 3 Cause of Loss is present, recorders are embedded directly
            // inside Paragraph 3 between Preamble and Post-Graph assessment (authentic Marine Cargo style).
            const hasCauseOfLoss = blocks.some(
              (b: any) => b.id === 'b_cause' || /cause of loss/i.test(b.section || headings[b.id] || '')
            );
            if (hasCauseOfLoss) {
              return null;
            }

            const included = isIncluded(block.included);
            return (
              <div
                key={block.id}
                className={`relative rounded-xl shadow-sm border p-5 ${
                  included ? 'bg-white border-gray-200' : 'bg-gray-50 border-dashed border-gray-300'
                }`}
              >
                <div className="absolute top-3 right-4 z-10">
                  <SectionToggle checked={included} onChange={(next) => handleBlockChange({ ...block, included: next })} />
                </div>
                {included ? (
                  <RecordersBlock block={block} reportId={report.id} onChange={handleBlockChange} isFormEditor={true} />
                ) : (
                  <div className="text-sm font-bold text-gray-400 uppercase tracking-wide line-through">
                    {block.title || 'Temperature recorder summary'}
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
            // A second fruit's table carries its own fruit; the first one
            // is the report's.
            const tableCommodity = (block.commodity || blockState?.metadata?.commodity) as string | undefined;
            const isLastTable = block.id === tableBlocks[tableBlocks.length - 1]?.id;
            return (
              <React.Fragment key={block.id}>
                <TableGrid
                  block={block}
                  reportId={report.id}
                  commodity={tableCommodity}
                  containers={shipmentContainers}
                  onChange={handleBlockChange}
                  onSaved={handleWorkbenchSaved}
                  onApply={handleSave}
                  dirty={dirty}
                  applying={saving}
                  onRemove={tableBlocks[0]?.id === block.id ? undefined : () => removeTable(block)}
                />
                {isLastTable && (
                  <AddFruitTable
                    reportId={report.id}
                    taken={tableBlocks.map((t: any) => t.commodity || blockState?.metadata?.commodity).filter(Boolean)}
                    onAdd={(nb) => addTableAfter(block.id, nb)}
                  />
                )}
              </React.Fragment>
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


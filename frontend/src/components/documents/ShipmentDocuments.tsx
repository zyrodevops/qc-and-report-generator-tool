/**
 * Shipment documents: upload the B/L (or sea / air waybill), invoice, packing
 * lists and recorder files; check what was read; fill the report.
 *
 * Nothing is written until the surveyor presses "Fill the report". Each value
 * shows which document it came from, rows can be edited or left out, and where
 * two documents disagree the difference is shown rather than settled.
 */
import React, { useRef, useState } from 'react';
import { AlertTriangle, CheckCircle2, FileText, Loader2, Thermometer, Upload, X } from 'lucide-react';
import {
  applyShipmentDocuments,
  DocumentsReadResult,
  ParticularsProposal,
  readShipmentDocuments,
} from '../../api/client';

interface Props {
  reportId: string;
  blockState: any;
  onApplied: (blockState: any, version: number) => void;
}

const current = (blockState: any, label: string): string => {
  const p = (blockState?.blocks || []).find((b: any) => b.type === 'particulars');
  const row = (p?.rows || []).find((r: any) => String(r.label).toLowerCase() === label.toLowerCase());
  const v = row ? (Array.isArray(row.value) ? row.value.join(', ') : String(row.value ?? '')) : '';
  return v.trim().startsWith('[') ? '' : v.trim();
};

export const ShipmentDocuments: React.FC<Props> = ({ reportId, blockState, onApplied }) => {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DocumentsReadResult | null>(null);
  const [rows, setRows] = useState<(ParticularsProposal & { keep: boolean })[]>([]);
  const [temp, setTemp] = useState('');
  const input = useRef<HTMLInputElement>(null);

  const applied = blockState?.metadata?.shipment;

  const read = async (files: FileList | null) => {
    if (!files?.length) return;
    setBusy(true);
    setError(null);
    try {
      const r = await readShipmentDocuments(reportId, Array.from(files));
      setResult(r);
      setRows(r.particulars.map((p) => ({ ...p, keep: true })));
      const t = r.shipment.requested_temperature_c;
      setTemp(Array.isArray(t) ? t.join(' to ') : t ?? '');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const apply = async () => {
    if (!result) return;
    setBusy(true);
    setError(null);
    try {
      const t = temp.trim();
      const parts = t.split(/\s*to\s*/i).filter(Boolean);
      const shipment = {
        ...result.shipment,
        requested_temperature_c: !t ? null : parts.length === 2 ? parts : parts[0],
      };
      const res = await applyShipmentDocuments(reportId, {
        particulars: rows.filter((r) => r.keep && r.value.trim()).map(({ label, value }) => ({ label, value })),
        shipment,
      });
      onApplied(res.block_state, res.version);
      setOpen(false);
      setResult(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const ship = result?.shipment || {};
  const recorders: any[] = ship.recorders || [];
  const containers: any[] = ship.containers || [];

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 font-bold text-gray-800">
          <FileText className="w-5 h-5 text-blue-600" />
          <span>Shipment documents</span>
          {applied?.document_number && (
            <span className="ml-2 inline-flex items-center gap-1 text-xs font-medium text-green-700 bg-green-50 border border-green-200 rounded px-2 py-0.5">
              <CheckCircle2 className="w-3.5 h-3.5" /> Filled from {applied.document_number}
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={() => {
            setOpen(true);
            setTimeout(() => input.current?.click(), 50);
          }}
          className="inline-flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-4 py-2 rounded-lg"
        >
          <Upload className="w-4 h-4" /> Upload B/L, invoice, packing lists, recorder files
        </button>
      </div>
      <p className="text-xs text-gray-500 mt-1">
        PDFs are read on this server. You check every value before anything goes into the report.
      </p>
      <input
        ref={input}
        type="file"
        accept="application/pdf,.pdf"
        multiple
        className="hidden"
        onChange={(e) => {
          read(e.target.files);
          e.target.value = '';
        }}
      />

      {open && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-start justify-center overflow-y-auto p-6">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-5xl">
            <div className="flex items-center justify-between px-5 py-3 border-b">
              <div className="font-bold text-gray-800">Check what was read from the documents</div>
              <button type="button" onClick={() => setOpen(false)} className="p-1 rounded hover:bg-gray-100">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-5 space-y-5">
              {busy && (
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <Loader2 className="w-4 h-4 animate-spin" /> Reading the documents…
                </div>
              )}
              {error && <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded p-2">{error}</div>}
              {!busy && !result && !error && (
                <button
                  type="button"
                  onClick={() => input.current?.click()}
                  className="w-full border-2 border-dashed border-gray-300 rounded-lg py-8 text-sm text-gray-600 hover:border-blue-400"
                >
                  Choose PDF files
                </button>
              )}

              {result && (
                <>
                  {/* Documents */}
                  <div>
                    <div className="text-xs font-semibold uppercase text-gray-400 mb-1.5">Documents</div>
                    <div className="flex flex-wrap gap-1.5">
                      {result.documents.map((d, i) => (
                        <span
                          key={i}
                          title={d.status || d.filename}
                          className={`text-[11px] px-2 py-0.5 rounded-full border ${
                            d.status ? 'border-amber-300 bg-amber-50 text-amber-800' : 'border-gray-200 bg-gray-50 text-gray-700'
                          }`}
                        >
                          <b>{d.kind_label}</b> · {d.filename}
                          {d.status ? ` — ${d.status}` : ''}
                        </span>
                      ))}
                    </div>
                  </div>

                  {(result.conflicts.length > 0 || result.notes.length > 0) && (
                    <div className="space-y-1.5">
                      {result.conflicts.map((c, i) => (
                        <div key={i} className="flex gap-2 text-xs text-red-800 bg-red-50 border border-red-200 rounded p-2">
                          <AlertTriangle className="w-4 h-4 shrink-0" />
                          <span>
                            <b>{c.field}</b> differs:{' '}
                            {c.values.map((v, j) => (
                              <span key={j}>
                                {j > 0 && ' vs '}“{v.value}” ({v.from})
                              </span>
                            ))}
                          </span>
                        </div>
                      ))}
                      {result.notes.map((n, i) => (
                        <div key={i} className="flex gap-2 text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded p-2">
                          <AlertTriangle className="w-4 h-4 shrink-0" /> {n}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Particulars */}
                  <div>
                    <div className="text-xs font-semibold uppercase text-gray-400 mb-1.5">Particulars</div>
                    {rows.length === 0 && <div className="text-sm text-gray-500">Nothing to fill from these documents.</div>}
                    <table className="w-full text-sm">
                      <tbody>
                        {rows.map((r, i) => {
                          const was = current(blockState, r.label);
                          return (
                            <tr key={r.label} className="border-t align-top">
                              <td className="py-1.5 pr-2 w-6">
                                <input
                                  type="checkbox"
                                  checked={r.keep}
                                  onChange={(e) => setRows((p) => p.map((x, j) => (j === i ? { ...x, keep: e.target.checked } : x)))}
                                />
                              </td>
                              <td className="py-1.5 pr-3 w-48 font-semibold text-gray-600 text-xs">{r.label}</td>
                              <td className="py-1.5">
                                <textarea
                                  value={r.value}
                                  rows={Math.min(4, Math.ceil(r.value.length / 90) || 1)}
                                  onChange={(e) => setRows((p) => p.map((x, j) => (j === i ? { ...x, value: e.target.value } : x)))}
                                  className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
                                />
                                <div className="text-[10px] text-gray-400">
                                  from {r.source || 'the documents'}
                                  {was && was !== r.value && <span className="text-amber-700"> · replaces “{was}”</span>}
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                        <tr className="border-t">
                          <td />
                          <td className="py-1.5 pr-3 font-semibold text-gray-600 text-xs">Requested temperature (°C)</td>
                          <td className="py-1.5">
                            <input
                              value={temp}
                              onChange={(e) => setTemp(e.target.value)}
                              placeholder="not on the documents"
                              className="w-40 border border-gray-300 rounded px-2 py-1 text-sm"
                            />
                            <span className="text-[10px] text-gray-400 ml-2">fills the requested temperature in the Cause of Loss wording</span>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  {containers.length > 0 && (
                    <div>
                      <div className="text-xs font-semibold uppercase text-gray-400 mb-1.5">Containers</div>
                      <table className="w-full text-xs border">
                        <thead className="bg-gray-50 text-gray-500">
                          <tr>
                            {['Container', 'Type', 'Seal', 'Packages', 'Pallets', 'Recorder'].map((h) => (
                              <th key={h} className="text-left px-2 py-1">{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {containers.map((c) => (
                            <tr key={c.container} className="border-t">
                              <td className="px-2 py-1 font-mono">{c.container}</td>
                              <td className="px-2 py-1">{c.type || '—'}</td>
                              <td className="px-2 py-1 font-mono">{c.seal || '—'}</td>
                              <td className="px-2 py-1">{c.packages || c.boxes_packing_list || '—'}</td>
                              <td className="px-2 py-1">{c.pallets || '—'}</td>
                              <td className="px-2 py-1 font-mono">{c.recorder_id || '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {recorders.length > 0 && (
                    <div>
                      <div className="text-xs font-semibold uppercase text-gray-400 mb-1.5 flex items-center gap-1">
                        <Thermometer className="w-3.5 h-3.5" /> Temperature recorders
                      </div>
                      <table className="w-full text-xs border">
                        <thead className="bg-gray-50 text-gray-500">
                          <tr>
                            {['Recorder', 'Container', 'Start', 'Stop', 'Highest', 'Lowest', 'Average', 'Readings'].map((h) => (
                              <th key={h} className="text-left px-2 py-1">{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {recorders.map((r, i) => (
                            <tr key={i} className="border-t">
                              <td className="px-2 py-1 font-mono">{r.summary?.device_id || '—'}</td>
                              <td className="px-2 py-1 font-mono">{r.container || '—'}</td>
                              <td className="px-2 py-1">{r.summary?.start || '—'}</td>
                              <td className="px-2 py-1">{r.summary?.stop || '—'}</td>
                              <td className="px-2 py-1">{r.summary?.highest_c ?? '—'} °C</td>
                              <td className="px-2 py-1">{r.summary?.lowest_c ?? '—'} °C</td>
                              <td className="px-2 py-1">{r.summary?.average_c ?? '—'} °C</td>
                              <td className="px-2 py-1">{r.readings?.toLocaleString?.() ?? r.readings}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      <div className="text-[10px] text-gray-400 mt-1">
                        Read exactly from the recorder files. They go into the report as a summary table with a graph each.
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>

            <div className="flex items-center justify-between px-5 py-3 border-t bg-gray-50 rounded-b-xl">
              <button type="button" onClick={() => input.current?.click()} className="text-sm text-blue-700 hover:underline">
                Add or change files
              </button>
              <div className="flex gap-2">
                <button type="button" onClick={() => setOpen(false)} className="px-4 py-2 text-sm rounded-lg hover:bg-gray-100">
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={!result || busy}
                  onClick={apply}
                  className="px-4 py-2 text-sm font-semibold rounded-lg bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50"
                >
                  Fill the report
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

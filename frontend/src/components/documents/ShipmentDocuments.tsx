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
import { CheckedScan, ScanReader } from './ScanReader';

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
  // Scans read by the online reader, checked by the surveyor: one entry per scanned document.
  const [scans, setScans] = useState<Record<string, CheckedScan>>({});
  const input = useRef<HTMLInputElement>(null);

  const applied = blockState?.metadata?.shipment;
  const gc = blockState?.metadata?.report_kind === 'general_cargo';
  const scanKey = (d: any) => `${d.asset_id}:${(d.pages || []).join(',')}`;

  const read = async (files: FileList | null) => {
    if (!files?.length) return;
    setBusy(true);
    setError(null);
    try {
      const r = await readShipmentDocuments(reportId, Array.from(files));
      setResult(r);
      setScans({});
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
      const kept = (kind: string) =>
        Object.values(scans).filter((s) => s.kind === kind).flatMap((s) => s.rows.filter((r) => r.keep));
      const hasContent = (r: any) => {
        if (r.type === 'table' || r.rows || r.headers) return true;
        if (typeof r.value === 'string') return Boolean(r.value.trim());
        if (Array.isArray(r.value)) return r.value.length > 0;
        return Boolean(r.value);
      };
      const res = await applyShipmentDocuments(reportId, {
        particulars: rows.filter((r) => r.keep && hasContent(r)).map((r) => {
          if (r.type === 'table' || r.rows || r.headers) {
            return {
              label: r.label,
              type: 'table',
              headers: r.headers || ['Commodity / Variety', 'Count / Size', 'Total Boxes'],
              rows: r.rows || r.items || [],
              footer: r.footer || '',
              value: r.value || [r.footer || ''],
              source: r.source,
            };
          }
          return {
            label: r.label,
            value: typeof r.value === 'string' ? r.value : Array.isArray(r.value) ? r.value.join(', ') : String(r.value || ''),
            source: r.source,
          };
        }),
        shipment: { ...shipment, lorry_receipts: kept('lorry_receipt').map(({ keep, flags, ...r }) => r) },
        weight_slips: kept('weight_slip').map(({ keep, flags, ...r }) => r),
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
          <Upload className="w-4 h-4" />{' '}
          {gc ? 'Upload B/L, invoice, packing lists, policy, weight slips' : 'Upload B/L, invoice, packing lists, recorder files'}
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
                                {r.type === 'table' || r.headers || r.rows ? (
                                  <div className="border border-slate-300 rounded overflow-hidden text-xs bg-white">
                                    <table className="w-full">
                                      <thead className="bg-slate-50 border-b border-slate-300 text-slate-700">
                                        <tr>
                                          <th className="p-1.5 text-left font-semibold">{(r.headers || ['Commodity / Variety', 'Count / Size', 'Total Boxes'])[0]}</th>
                                          <th className="p-1.5 text-center font-semibold">{(r.headers || ['Commodity / Variety', 'Count / Size', 'Total Boxes'])[1]}</th>
                                          <th className="p-1.5 text-right font-semibold">{(r.headers || ['Commodity / Variety', 'Count / Size', 'Total Boxes'])[2]}</th>
                                        </tr>
                                      </thead>
                                      <tbody>
                                        {(r.rows || r.items || []).map((it: any, sIdx: number) => (
                                          <tr key={sIdx} className="border-b border-slate-100">
                                            <td className="p-1.5">{it.col1 ?? it.variety ?? it.description ?? ''}</td>
                                            <td className="p-1.5 text-center">{it.col2 ?? it.count ?? it.size ?? ''}</td>
                                            <td className="p-1.5 text-right">{it.col3 ?? it.boxes ?? it.cartons ?? ''}</td>
                                          </tr>
                                        ))}
                                        {r.footer && (
                                          <tr className="bg-slate-50 font-bold border-t border-slate-300">
                                            <td colSpan={3} className="p-1.5">{r.footer}</td>
                                          </tr>
                                        )}
                                      </tbody>
                                    </table>
                                    <div className="text-[10px] text-gray-400 p-1 bg-slate-50 border-t border-slate-200">
                                      from {r.source || 'the documents'}
                                    </div>
                                  </div>
                                ) : (
                                  <>
                                    <textarea
                                      value={typeof r.value === 'string' ? r.value : Array.isArray(r.value) ? r.value.join('\n') : String(r.value || '')}
                                      rows={Math.min(4, Math.ceil((typeof r.value === 'string' ? r.value.length : 20) / 90) || 1)}
                                      onChange={(e) => setRows((p) => p.map((x, j) => (j === i ? { ...x, value: e.target.value } : x)))}
                                      className="w-full border border-gray-300 rounded px-2 py-1 text-sm font-sans"
                                    />
                                    <div className="text-[10px] text-gray-400">
                                      from {r.source || 'the documents'}
                                      {was && was !== r.value && <span className="text-amber-700"> · replaces “{was}”</span>}
                                    </div>
                                  </>
                                )}
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

                  {result.documents.some((d) => d.scan) && (
                    <div className="space-y-2">
                      <div className="text-xs font-semibold uppercase text-gray-400">Scanned documents</div>
                      {result.documents
                        .filter((d) => d.scan)
                        .map((d) => (
                          <ScanReader
                            key={scanKey(d)}
                            reportId={reportId}
                            doc={d}
                            containers={containers}
                            value={scans[scanKey(d)]}
                            onChange={(v) =>
                              setScans((prev) => {
                                const next = { ...prev };
                                if (v) next[scanKey(d)] = v;
                                else delete next[scanKey(d)];
                                return next;
                              })
                            }
                          />
                        ))}
                    </div>
                  )}

                  {gc && containers.length > 0 && (
                    <div>
                      <div className="text-xs font-semibold uppercase text-gray-400 mb-1.5">Containers</div>
                      <table className="w-full text-xs border" data-testid="gc-containers">
                        <thead className="bg-gray-50 text-gray-500">
                          <tr>
                            {['Container', 'Type', 'Seal', 'Tare (B/L)', 'Gross (packing list)', 'Discharged', 'To consignee', 'Delivered to (EIR)'].map((h) => (
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
                              <td className="px-2 py-1">{c.tare_kg || '—'}</td>
                              <td className="px-2 py-1">{c.pl_gross_kg || '—'}</td>
                              <td className="px-2 py-1">{c.tracking?.discharged || '—'}</td>
                              <td className="px-2 py-1">{c.tracking?.to_consignee || '—'}</td>
                              <td className="px-2 py-1">{c.eir?.destination || '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {!gc && containers.length > 0 && (
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

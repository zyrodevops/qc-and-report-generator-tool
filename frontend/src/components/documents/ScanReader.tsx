/**
 * Scanned weight slips and lorry receipts, read by the online reader.
 *
 * Nothing it reads goes into the report as it is: every value is shown in an
 * editable table, anything that looks wrong is marked (a container number
 * that fails its check digit, gross − tare ≠ net), and the surveyor keeps,
 * corrects or clears each row. When the reader cannot be reached the reason
 * is shown and the figures are typed in instead, here or in the survey
 * paragraph's weighbridge table.
 */
import React, { useState } from 'react';
import { AlertTriangle, Loader2, ScanLine } from 'lucide-react';
import { readScan, ScanRow, ShipmentDocumentRead } from '../../api/client';

export type ScanKind = 'weight_slip' | 'lorry_receipt';

export interface CheckedScan {
  kind: ScanKind;
  rows: (ScanRow & { keep: boolean; tare_of?: 'container' | 'truck' })[];
}

const COLUMNS: Record<ScanKind, { key: string; label: string; w?: string }[]> = {
  weight_slip: [
    { key: 'container_no', label: 'Container', w: 'w-32' },
    { key: 'weighbridge', label: 'Weighbridge' },
    { key: 'slip_no', label: 'Slip no.', w: 'w-20' },
    { key: 'date', label: 'Date', w: 'w-28' },
    { key: 'gross_kg', label: 'Gross kg', w: 'w-20' },
    { key: 'tare_kg', label: 'Tare kg', w: 'w-20' },
    { key: 'net_kg', label: 'Net kg', w: 'w-20' },
  ],
  lorry_receipt: [
    { key: 'lr_no', label: 'LR no.', w: 'w-24' },
    { key: 'date', label: 'Date', w: 'w-28' },
    { key: 'truck_no', label: 'Truck', w: 'w-28' },
    { key: 'from_place', label: 'From' },
    { key: 'to_place', label: 'To' },
    { key: 'packages', label: 'Packages', w: 'w-24' },
    { key: 'remarks', label: 'Remarks' },
  ],
};

/** A container's tare is about 2–4.5 t; a truck's is much more (as the server's first guess). */
function tareGuess(row: ScanRow, blTare?: string): 'container' | 'truck' {
  const t = Number(String(row.tare_kg ?? '').replace(/,/g, ''));
  if (!Number.isFinite(t) || !row.tare_kg) return 'truck';
  const b = Number(String(blTare ?? '').replace(/,/g, ''));
  if (blTare && Number.isFinite(b)) return Math.abs(t - b) <= 50 ? 'container' : 'truck';
  return t < 5000 ? 'container' : 'truck';
}

interface Props {
  reportId: string;
  doc: ShipmentDocumentRead;
  /** Containers from the documents, for the B/L tare. */
  containers: any[];
  value?: CheckedScan;
  onChange: (v: CheckedScan | undefined) => void;
}

export const ScanReader: React.FC<Props> = ({ reportId, doc, containers, value, onChange }) => {
  const initialKind: ScanKind = doc.kind === 'lorry_receipt' ? 'lorry_receipt' : 'weight_slip';
  const [kind, setKind] = useState<ScanKind>(value?.kind || initialKind);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const read = async () => {
    if (!doc.asset_id || !doc.pages?.length) return;
    setBusy(true);
    setError(null);
    try {
      const res = await readScan(reportId, { asset_id: doc.asset_id, pages: doc.pages, kind });
      if (res.error) setError(res.error);
      const bl = (c: string) => containers.find((x) => x.container === c)?.tare_kg;
      onChange({
        kind,
        rows: res.rows.map((r) => ({ ...r, keep: !(r.flags || []).includes('not read'), tare_of: tareGuess(r, bl(r.container_no)) })),
      });
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const edit = (i: number, patch: Record<string, any>) =>
    value && onChange({ ...value, rows: value.rows.map((r, j) => (j === i ? { ...r, ...patch } : r)) });
  const cols = COLUMNS[value?.kind || kind];

  return (
    <div className="border border-gray-200 rounded-lg p-3 space-y-2" data-testid="scan-reader">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <ScanLine className="w-4 h-4 text-violet-600" />
        <b className="text-gray-800">{doc.filename}</b>
        <span className="text-gray-500">({doc.pages?.length || 0} page{(doc.pages?.length || 0) > 1 ? 's' : ''}, scanned)</span>
        <select aria-label="What the scan is" value={kind} onChange={(e) => setKind(e.target.value as ScanKind)}
          className="border border-gray-300 rounded px-1.5 py-0.5">
          <option value="weight_slip">Weight slips</option>
          <option value="lorry_receipt">Lorry receipt / consignment note</option>
        </select>
        <button type="button" disabled={busy} onClick={read}
          className="inline-flex items-center gap-1 px-2 py-1 rounded bg-violet-600 hover:bg-violet-700 text-white font-semibold disabled:opacity-50">
          {busy ? <Loader2 className="w-3 h-3 animate-spin" /> : <ScanLine className="w-3 h-3" />}
          {busy ? 'Reading…' : value ? 'Read again' : 'Read online'}
        </button>
        {value && (
          <button type="button" onClick={() => onChange(undefined)} className="text-gray-500 hover:text-gray-800">
            Clear
          </button>
        )}
      </div>
      {error && (
        <div className="flex items-center gap-1 text-[11px] text-amber-800 bg-amber-50 border border-amber-200 rounded px-2 py-1">
          <AlertTriangle className="w-3.5 h-3.5" /> {error} You can type the figures in the survey paragraph's weighbridge table.
        </div>
      )}
      {value && value.rows.length > 0 && (
        <>
          <div className="text-[10.5px] text-violet-800">Read online. Check every value; untick a row to leave it out.</div>
          <div className="overflow-x-auto">
            <table className="w-full text-[11px]">
              <thead className="text-gray-500">
                <tr>
                  <th className="text-left px-1">Use</th>
                  <th className="text-left px-1">Page</th>
                  {cols.map((c) => <th key={c.key} className="text-left px-1">{c.label}</th>)}
                  {value.kind === 'weight_slip' && <th className="text-left px-1">Tare is the</th>}
                  <th className="text-left px-1">Check</th>
                </tr>
              </thead>
              <tbody>
                {value.rows.map((r, i) => (
                  <tr key={i} className="border-t align-top">
                    <td className="px-1 py-0.5">
                      <input type="checkbox" aria-label={`Use page ${r.page}`} checked={r.keep} onChange={(e) => edit(i, { keep: e.target.checked })} />
                    </td>
                    <td className="px-1 py-0.5 text-gray-500">{r.page}</td>
                    {cols.map((c) => (
                      <td key={c.key} className={`px-1 py-0.5 ${c.w || ''}`}>
                        <input value={r[c.key] ?? ''} aria-label={`${c.label} page ${r.page}`}
                          onChange={(e) => edit(i, { [c.key]: e.target.value })}
                          className="w-full border border-gray-200 rounded px-1 py-0.5 font-mono" />
                      </td>
                    ))}
                    {value.kind === 'weight_slip' && (
                      <td className="px-1 py-0.5">
                        <select aria-label={`Tare of page ${r.page}`} value={r.tare_of || 'truck'}
                          onChange={(e) => edit(i, { tare_of: e.target.value })} className="border border-gray-200 rounded px-1 py-0.5">
                          <option value="container">container's</option>
                          <option value="truck">truck's</option>
                        </select>
                      </td>
                    )}
                    <td className="px-1 py-0.5 text-red-700">{(r.flags || []).join('; ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {value.kind === 'weight_slip' && (
            <div className="text-[10px] text-gray-500">
              Kept rows go into the weighbridge table of each container's survey paragraph (one is added if a container has none).
              Figures already typed there are not replaced.
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default ScanReader;

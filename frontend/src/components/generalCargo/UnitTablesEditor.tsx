import React from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { fmt, tally, weighbridge } from '../../utils/gcTables';

interface Props {
  block: any;
  onChange: (b: any) => void;
  /** This paragraph's container as the documents give it (packing-list gross, B/L tare). */
  fromDocuments?: any;
}

/** What the documents say of this container, to start the weighbridge table from. */
function weightsFromDocuments(doc: any): Record<string, string> {
  if (!doc) return { basis: 'B/L' };
  const out: Record<string, string> = { basis: doc.pl_gross_kg ? 'Packing List' : 'B/L' };
  const declared = doc.pl_gross_kg || doc.gross_kg;
  if (declared) out.declared = String(declared);
  if (doc.tare_kg) out.tare_container = String(doc.tare_kg);
  return out;
}

const BASES = ['B/L', 'Packing List', 'Invoice', 'Bill of Entry', 'Weight slip'];
const input = 'px-2 py-1 border border-gray-300 rounded text-xs w-full';

/**
 * A survey paragraph's weighbridge figures and tally. What is worked out
 * (found weight, shortage / excess) is shown here as it will print.
 */
export const UnitTablesEditor: React.FC<Props> = ({ block, onChange, fromDocuments }) => {
  const w = block.weights || {};
  const t = block.tally || {};
  const hasW = Boolean(block.weights);
  const hasT = Boolean(block.tally);
  const setW = (patch: any) => onChange({ ...block, weights: { ...w, ...patch } });
  const setT = (patch: any) => onChange({ ...block, tally: { ...t, ...patch } });
  const wb = weighbridge(block);
  const tt = tally(block);
  const tRows: any[] = t.rows || [];

  const wField = (key: string, label: string, numeric = false) => (
    <label className="text-[10px] text-gray-500 flex flex-col gap-0.5">
      {label}
      <input className={input} aria-label={label} value={w[key] || ''} inputMode={numeric ? 'decimal' : undefined}
        onChange={(e) => setW({ [key]: e.target.value })} />
    </label>
  );

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-4 text-sm">
        <label className="inline-flex items-center gap-1.5 cursor-pointer select-none">
          <input type="checkbox" checked={hasW}
            onChange={(e) => onChange({ ...block, weights: e.target.checked ? { ...weightsFromDocuments(fromDocuments), ...(block.weights_off || {}) } : undefined, weights_off: e.target.checked ? undefined : block.weights })} />
          Weighed at a weighbridge
        </label>
        <label className="inline-flex items-center gap-1.5 cursor-pointer select-none">
          <input type="checkbox" checked={hasT}
            onChange={(e) => onChange({ ...block, tally: e.target.checked ? { basis: 'Packing List', rows: [{}], ...(block.tally_off || {}) } : undefined, tally_off: e.target.checked ? undefined : block.tally })} />
          Tally against the documents
        </label>
      </div>

      {hasW && (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 space-y-2" data-testid="weight-editor">
          <div className="text-xs font-bold text-gray-700">Weighbridge (kg)</div>
          <div className="grid grid-cols-3 gap-2">
            {wField('weighbridge', 'Weighbridge name')}
            {wField('slip_no', 'Slip no.')}
            {wField('date', 'Slip date')}
            {wField('gross', 'Gross (truck + container + cargo)', true)}
            {wField('tare_truck', 'Tare of truck', true)}
            {wField('tare_container', 'Tare of container (as marked)', true)}
            {wField('declared', 'Gross weight as per document', true)}
            <label className="text-[10px] text-gray-500 flex flex-col gap-0.5">
              Document
              <select className={input} aria-label="Weight document" value={w.basis || 'B/L'} onChange={(e) => setW({ basis: e.target.value })}>
                {BASES.map((b) => <option key={b}>{b}</option>)}
              </select>
            </label>
          </div>
          {wb && (
            <div className="text-xs text-gray-700" data-testid="weight-result">
              {wb.found !== null && <span>Found: <b>{fmt(wb.found)} kg</b></span>}
              {wb.diff !== null && (
                <span className={`ml-3 ${wb.diff < 0 ? 'text-red-700' : wb.diff > 0 ? 'text-green-700' : ''}`}>
                  {wb.diff < 0 ? 'Shortage' : wb.diff > 0 ? 'Excess' : 'Difference'}: <b>{fmt(Math.abs(wb.diff))} kg</b>
                </span>
              )}
            </div>
          )}
        </div>
      )}

      {hasT && (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 space-y-2" data-testid="tally-editor">
          <div className="flex items-center gap-2 text-xs">
            <span className="font-bold text-gray-700">Tally</span>
            <span className="text-gray-500">quantities as per</span>
            <select className="px-1.5 py-0.5 border border-gray-300 rounded text-xs" aria-label="Tally document" value={t.basis || 'Packing List'}
              onChange={(e) => setT({ basis: e.target.value })}>
              {BASES.map((b) => <option key={b}>{b}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-[1.6fr_0.8fr_0.8fr_0.8fr_0.9fr_auto] gap-1 text-[10px] font-semibold text-gray-500">
            <span>Description</span><span>As per document</span><span>Found sound</span><span>Found damaged</span><span>Short / excess</span><span />
          </div>
          {tRows.map((r, i) => (
            <div key={i} className="grid grid-cols-[1.6fr_0.8fr_0.8fr_0.8fr_0.9fr_auto] gap-1 items-center">
              {(['item', 'document', 'sound', 'damaged'] as const).map((k) => (
                <input key={k} className={input} aria-label={`Tally ${k} ${i + 1}`} value={r[k] || ''}
                  onChange={(e) => setT({ rows: tRows.map((x, j) => (j === i ? { ...x, [k]: e.target.value } : x)) })} />
              ))}
              <span className="text-xs font-semibold text-gray-700">{tt?.rows[i]?.[4] ?? ''}</span>
              <button type="button" aria-label={`Remove tally line ${i + 1}`} className="p-1 text-gray-400 hover:text-red-600"
                onClick={() => setT({ rows: tRows.filter((_, j) => j !== i) })}>
                <Trash2 size={13} />
              </button>
            </div>
          ))}
          <button type="button" onClick={() => setT({ rows: [...tRows, {}] })} className="inline-flex items-center gap-1 text-xs text-blue-700 hover:text-blue-900">
            <Plus size={12} /> Add a line
          </button>
          {tt?.total && <div className="text-xs text-gray-700">Total short / excess: <b>{tt.rows[tt.rows.length - 1][4]}</b></div>}
        </div>
      )}
    </div>
  );
};

export default UnitTablesEditor;

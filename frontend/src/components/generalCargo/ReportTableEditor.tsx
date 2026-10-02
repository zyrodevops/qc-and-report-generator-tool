import React from 'react';
import { Plus, Table2, Trash2 } from 'lucide-react';
import { REPORT_TABLE_FIELDS, REPORT_TABLE_NAMES, reportTable, sealTallies } from '../../utils/gcTables';

interface Props {
  block: any;
  onChange: (b: any) => void;
  /** Containers on the cover and their seal numbers, to start the seals table from. */
  containers?: string[];
  seals?: string[];
}

const input = 'px-2 py-1 border border-gray-300 rounded text-xs w-full';

/**
 * A general cargo report table: containers & seals, weather, or summary of
 * reserve. Off until ticked. What is worked out (seals tally, the total) is
 * shown as it will print.
 */
export const ReportTableEditor: React.FC<Props> = ({ block, onChange, containers = [], seals = [] }) => {
  const fields = REPORT_TABLE_FIELDS[block.kind] || [];
  const rows: any[] = block.rows || [];
  const on = block.included !== false;
  const printed = reportTable(block);
  const set = (next: any[]) => onChange({ ...block, rows: next });

  const fillContainers = () => {
    const known = new Set(rows.map((r) => String(r.container || '').trim()));
    const added = containers.filter((c) => c && !known.has(c)).map((c, i) => ({ container: c, seal_doc: seals.length === containers.length ? seals[i] : '' }));
    set([...rows.filter((r) => Object.values(r).some((v) => String(v || '').trim())), ...added]);
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 space-y-2" data-testid={`gc-table-${block.kind}`}>
      <label className="flex items-center gap-2 text-sm font-bold text-gray-800 cursor-pointer select-none">
        <input type="checkbox" checked={on} onChange={(e) => onChange({ ...block, included: e.target.checked, rows: rows.length ? rows : [{}] })} />
        <Table2 className="w-4 h-4 text-blue-600" />
        {REPORT_TABLE_NAMES[block.kind] || 'Table'}
        {!on && <span className="text-xs font-normal text-gray-400">(not in the report)</span>}
      </label>
      {on && (
        <>
          {block.kind === 'reserve' && (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-gray-600">Currency</span>
              {['USD', 'INR'].map((c) => (
                <button key={c} type="button" aria-pressed={block.currency === c}
                  onClick={() => onChange({ ...block, currency: c })}
                  className={`px-2 py-0.5 rounded-full border ${block.currency === c ? 'border-blue-500 bg-blue-50 text-blue-800 font-semibold' : 'border-gray-300 text-gray-600'}`}>
                  {c}
                </button>
              ))}
            </div>
          )}
          <div className="grid gap-1 text-[10px] font-semibold text-gray-500" style={{ gridTemplateColumns: `repeat(${fields.length}, minmax(0,1fr)) 5rem auto` }}>
            {fields.map((f) => <span key={f.key}>{f.label}</span>)}
            <span>{block.kind === 'seals' ? 'Tallies' : ''}</span>
            <span />
          </div>
          {rows.map((r, i) => (
            <div key={i} className="grid gap-1 items-center" style={{ gridTemplateColumns: `repeat(${fields.length}, minmax(0,1fr)) 5rem auto` }}>
              {fields.map((f) => (
                <input key={f.key} className={input} aria-label={`${f.label} ${i + 1}`} value={r[f.key] || ''}
                  onChange={(e) => set(rows.map((x, j) => (j === i ? { ...x, [f.key]: e.target.value } : x)))} />
              ))}
              <span className="text-xs font-semibold text-gray-700">
                {block.kind === 'seals' ? sealTallies(r.seal_doc, r.seal_found) : ''}
              </span>
              <button type="button" aria-label={`Remove row ${i + 1}`} className="p-1 text-gray-400 hover:text-red-600" onClick={() => set(rows.filter((_, j) => j !== i))}>
                <Trash2 size={13} />
              </button>
            </div>
          ))}
          <div className="flex items-center gap-3">
            <button type="button" onClick={() => set([...rows, {}])} className="inline-flex items-center gap-1 text-xs text-blue-700 hover:text-blue-900">
              <Plus size={12} /> Add a row
            </button>
            {block.kind === 'seals' && containers.length > 0 && (
              <button type="button" onClick={fillContainers} className="text-xs text-blue-700 hover:text-blue-900">
                Fill the containers from the cover
              </button>
            )}
            {block.kind === 'reserve' && printed?.total && (
              <span className="text-xs text-gray-700">Total: <b>{printed.rows[printed.rows.length - 1][2]}</b></span>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default ReportTableEditor;

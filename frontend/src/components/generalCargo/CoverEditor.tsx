import React, { useState } from 'react';
import { FileText, Plus, X } from 'lucide-react';

interface Props {
  block: any;
  onChange: (b: any) => void;
}

const valueText = (v: any) => (Array.isArray(v) ? v.join(', ') : String(v ?? ''));

/**
 * The cover of a general cargo report. Its fields differ from case to case in
 * the client's reports (one has seven insurers and no B/L, another five
 * dates), so fields can be added, renamed and removed here.
 */
export const CoverEditor: React.FC<Props> = ({ block, onChange }) => {
  const rows: any[] = block.rows || [];
  const known: string[] = block.optional_labels || [];
  const [adding, setAdding] = useState('');
  const listId = `cover-labels-${block.id}`;
  const unused = known.filter((l) => !rows.some((r) => r.label === l));

  const setRow = (i: number, patch: any) => {
    const next = [...rows];
    next[i] = { ...next[i], ...patch };
    onChange({ ...block, rows: next });
  };
  const removeRow = (i: number) => {
    const r = rows[i];
    const v = valueText(r.value).trim();
    const filled = v && !/^\[.*\]$/.test(v);
    if (filled && !window.confirm(`Remove "${r.label}"? Its value will be deleted.`)) return;
    onChange({ ...block, rows: rows.filter((_, j) => j !== i) });
  };
  const addRow = () => {
    const label = adding.trim();
    if (!label) return;
    onChange({ ...block, rows: [...rows, { label, value: [`[${label.replace(/\.$/, '')}]`] }] });
    setAdding('');
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4" data-testid="gc-cover">
      <div className="flex items-center gap-2 pb-2 border-b border-gray-100 font-bold text-gray-800">
        <FileText className="w-5 h-5 text-blue-600" />
        <span>Cover — particulars</span>
        <span className="text-xs font-normal text-gray-500 ml-2">Add, rename or remove fields as the case needs.</span>
      </div>
      <div className="space-y-2">
        {rows.map((r, i) => (
          <div key={i} className="grid grid-cols-[14rem_1fr_auto] gap-2 items-start">
            <input
              value={r.label}
              aria-label={`Field name ${i + 1}`}
              onChange={(e) => setRow(i, { label: e.target.value })}
              className="px-2 py-1.5 border border-gray-200 rounded text-xs font-semibold text-gray-600 bg-gray-50 outline-none focus:ring-1 focus:ring-blue-500"
            />
            <textarea
              value={valueText(r.value)}
              aria-label={r.label}
              rows={Math.min(6, Math.max(1, valueText(r.value).split('\n').length))}
              onChange={(e) => setRow(i, { value: [e.target.value] })}
              className="px-3 py-1.5 border border-gray-300 rounded text-sm outline-none focus:ring-1 focus:ring-blue-500 resize-y"
            />
            <button
              type="button"
              onClick={() => removeRow(i)}
              className="p-1.5 text-gray-300 hover:text-red-500"
              title={`Remove ${r.label}`}
              aria-label={`Remove ${r.label}`}
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>
      <div className="flex items-center gap-2 pt-1">
        <input
          list={listId}
          value={adding}
          aria-label="New field name"
          placeholder="Add a field — pick one or type your own"
          onChange={(e) => setAdding(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addRow())}
          className="w-80 px-2 py-1.5 border border-gray-300 rounded text-sm outline-none focus:ring-1 focus:ring-blue-500"
        />
        <datalist id={listId}>
          {unused.map((l) => (
            <option key={l} value={l} />
          ))}
        </datalist>
        <button
          type="button"
          onClick={addRow}
          disabled={!adding.trim()}
          className="flex items-center gap-1 text-sm bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white font-medium px-3 py-1.5 rounded"
        >
          <Plus className="w-4 h-4" /> Add field
        </button>
      </div>
    </div>
  );
};

export default CoverEditor;

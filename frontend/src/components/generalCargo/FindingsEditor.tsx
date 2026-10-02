import React, { useState } from 'react';
import { Plus, Trash2, Wand2 } from 'lucide-react';
import { pickClauses, ClauseContext } from '../../api/client';
import { Finding, writeFindings } from '../../utils/generalCargo';

const EMPTY: Finding = { item: '', total: '', affected: '', condition: '', photos: '' };
// Suggestions only; the surveyor types what he found.
const CONDITIONS = ['wet', 'torn', 'cut / torn', 'dented', 'broken', 'crushed', 'rusted', 'leaking', 'stained', 'punctured',
  'bulged', 'missing', 'short'];

interface Props {
  block: any;
  onChange: (b: any) => void;
  clauseContext?: ClauseContext;
}

/**
 * What was found, as a list: packages, how many, condition, photos. It
 * prints as the damage table of this survey paragraph; "Write into the text"
 * adds the reports' line before the table and "the remaining … were found in
 * an apparently sound condition" for what is left over.
 */
export const FindingsEditor: React.FC<Props> = ({ block, onChange, clauseContext }) => {
  const rows: Finding[] = block.findings || [];
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState('');
  const set = (next: Finding[]) => onChange({ ...block, findings: next });
  const edit = (i: number, key: keyof Finding, v: string) => set(rows.map((r, j) => (j === i ? { ...r, [key]: v } : r)));
  const listId = `conditions-${block.id}`;

  const write = async () => {
    setBusy(true);
    setNote('');
    try {
      const res = clauseContext ? await pickClauses('survey_findings', clauseContext) : null;
      const text = writeFindings(rows, res?.patterns || {});
      const added = { ...(block.wording_added || {}) };
      const old = added.findings;
      const current = String(block.additional_text || '');
      const next = old && current.includes(old) ? current.replace(old, text) : [current.trim(), text].filter(Boolean).join('\n\n');
      added.findings = text;
      onChange({ ...block, additional_text: next, wording_added: added, findings_table: block.findings_table !== false });
      if (!res?.patterns?.lead) setNote('No standard wording loaded; only the table’s place was added.');
    } catch {
      setNote('Could not load the standard wording. Try again.');
    } finally {
      setBusy(false);
    }
  };

  const cell = 'px-2 py-1 border border-gray-300 rounded text-xs w-full';
  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 space-y-2" data-testid="findings-editor">
      <div className="flex items-center justify-between">
        <div className="text-xs font-bold text-gray-700">Damage found (prints as a table)</div>
        <label className="text-[11px] text-gray-600 flex items-center gap-1">
          <input
            type="checkbox"
            checked={block.findings_table !== false}
            onChange={(e) => onChange({ ...block, findings_table: e.target.checked })}
          />
          Print the table
        </label>
      </div>
      {rows.length > 0 && (
        <div className="grid grid-cols-[1.4fr_0.7fr_0.7fr_1.2fr_1fr_auto] gap-1 text-[10px] font-semibold text-gray-500">
          <span>Packages / item</span>
          <span>Total</span>
          <span>Affected</span>
          <span>Condition found</span>
          <span>Photo Nos.</span>
          <span />
        </div>
      )}
      {rows.map((r, i) => (
        <div key={i} className="grid grid-cols-[1.4fr_0.7fr_0.7fr_1.2fr_1fr_auto] gap-1">
          <input className={cell} aria-label={`Item ${i + 1}`} value={r.item} placeholder="e.g. bags" onChange={(e) => edit(i, 'item', e.target.value)} />
          <input className={cell} aria-label={`Total ${i + 1}`} value={r.total} inputMode="numeric" onChange={(e) => edit(i, 'total', e.target.value)} />
          <input className={cell} aria-label={`Affected ${i + 1}`} value={r.affected} inputMode="numeric" onChange={(e) => edit(i, 'affected', e.target.value)} />
          <input className={cell} aria-label={`Condition ${i + 1}`} value={r.condition} list={listId} onChange={(e) => edit(i, 'condition', e.target.value)} />
          <input className={cell} aria-label={`Photos ${i + 1}`} value={r.photos} placeholder="e.g. 5 to 12" onChange={(e) => edit(i, 'photos', e.target.value)} />
          <button type="button" aria-label={`Remove line ${i + 1}`} className="p-1 text-gray-400 hover:text-red-600" onClick={() => set(rows.filter((_, j) => j !== i))}>
            <Trash2 size={13} />
          </button>
        </div>
      ))}
      <datalist id={listId}>
        {CONDITIONS.map((c) => (
          <option key={c} value={c} />
        ))}
      </datalist>
      <div className="flex items-center gap-2">
        <button type="button" onClick={() => set([...rows, { ...EMPTY, item: rows[rows.length - 1]?.item || '', total: rows[rows.length - 1]?.total || '' }])}
          className="inline-flex items-center gap-1 text-xs text-blue-700 hover:text-blue-900">
          <Plus size={12} /> Add a line
        </button>
        {rows.length > 0 && (
          <button type="button" disabled={busy} onClick={write}
            className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-60">
            <Wand2 size={12} /> Write into the text
          </button>
        )}
        {note && <span className="text-[11px] text-amber-700">{note}</span>}
      </div>
    </div>
  );
};

export default FindingsEditor;

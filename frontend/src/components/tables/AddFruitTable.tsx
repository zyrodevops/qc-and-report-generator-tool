import React, { useEffect, useState } from 'react';
import { Plus, Loader2 } from 'lucide-react';
import { CommodityArchetype, fetchCommodities, newFruitTable } from '../../api/client';

interface AddFruitTableProps {
  reportId: string;
  /** Fruits that already have a table; they are not offered again. */
  taken: string[];
  onAdd: (block: any) => void;
}

/**
 * For a cargo of more than one fruit: adds a condition-found table laid out
 * for the other fruit — its own columns and unit (kg for grapes, pieces for
 * apples). The fruit is always chosen here; none is assumed.
 */
export const AddFruitTable: React.FC<AddFruitTableProps> = ({ reportId, taken, onAdd }) => {
  const [open, setOpen] = useState(false);
  const [fruits, setFruits] = useState<CommodityArchetype[]>([]);
  const [choice, setChoice] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || fruits.length) return;
    fetchCommodities('FRUITS')
      .then(setFruits)
      .catch((e) => setError(e.message || 'Could not load the fruit list.'));
  }, [open, fruits.length]);

  const takenSet = new Set(taken.map((t) => t.toUpperCase()));
  // Keys are spelt both ways in places (GRAPES / GRAPE), so compare without a final S.
  const bare = (k: string) => k.toUpperCase().replace(/S$/, '');
  const offered = fruits.filter((f) => ![...takenSet].some((t) => bare(t) === bare(f.key)));

  const add = async () => {
    if (!choice) return;
    setBusy(true);
    setError(null);
    try {
      onAdd(await newFruitTable(reportId, choice));
      setOpen(false);
      setChoice('');
    } catch (e: any) {
      setError(e.message || 'Could not add the table.');
    } finally {
      setBusy(false);
    }
  };

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="w-full flex items-center justify-center gap-1.5 text-sm text-blue-700 font-medium py-2.5 rounded-xl border border-dashed border-blue-300 bg-blue-50/40 hover:bg-blue-50 transition"
      >
        <Plus className="w-4 h-4" />
        Add a table for another fruit
      </button>
    );
  }

  return (
    <div className="rounded-xl border border-blue-200 bg-blue-50/40 p-4 space-y-2">
      <div className="text-sm font-semibold text-gray-800">Which other fruit is in this cargo?</div>
      <div className="flex items-center gap-2 flex-wrap">
        <select
          value={choice}
          onChange={(e) => setChoice(e.target.value)}
          aria-label="Fruit for the new table"
          className="px-3 py-1.5 border border-gray-300 rounded text-sm bg-white outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="">Choose a fruit…</option>
          {offered.map((f) => (
            <option key={f.key} value={f.key}>
              {f.display} ({f.unit})
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={add}
          disabled={!choice || busy}
          className="flex items-center gap-1 text-sm bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium px-3 py-1.5 rounded transition"
        >
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
          Add table
        </button>
        <button
          type="button"
          onClick={() => {
            setOpen(false);
            setChoice('');
            setError(null);
          }}
          className="text-sm text-gray-600 hover:text-gray-800 px-2 py-1.5"
        >
          Cancel
        </button>
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
};

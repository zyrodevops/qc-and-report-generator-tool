import React, { useMemo, useState } from 'react';
import { Table, Upload, Plus, Trash2, ScanLine, X, Check, Loader2 } from 'lucide-react';
import { VerificationWorkbench } from './VerificationWorkbench';
import { columnTitle } from '../../utils/labels';
import { SectionToggle, isIncluded } from '../SectionToggle';

interface Category {
  key: string;
  label: string;
  role?: 'sound' | 'defect' | 'extra';
}

interface TableRow {
  group: string;
  boxes_opened?: number;
  values: Record<string, number | string>;
  stated_total?: number | null;
  provenance?: string;
}

interface TableBlockProps {
  block: {
    id: string;
    title?: string;
    unit?: string;
    grouping_label?: string;
    categories: Category[];
    rows: TableRow[];
    show_title?: boolean;
    show_chart?: boolean;
  };
  onChange: (updatedBlock: any) => void;
  reportId?: string;
  /** Called after the workbench saves, with the server's new state and version. */
  onSaved?: (updatedBlockState: any, version: number) => void;
  /** Saves the report. Shown as "Apply changes" while there are unsaved edits. */
  onApply?: () => Promise<unknown> | void;
  dirty?: boolean;
  applying?: boolean;
  /** Decides which defect columns the tally grid offers. */
  commodity?: string;
}

/** A cell's number, or null when nothing has been entered. */
const toNumber = (v: unknown): number | null => {
  if (v === null || v === undefined) return null;
  const s = String(v).trim();
  if (s === '') return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
};

const toKey = (label: string) =>
  label.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');

/**
 * The defect table on the report form.
 *
 * Rows and columns can be added and removed here as well as in the workbench,
 * so a surveyor who comes back to a saved report can correct it in place.
 * Nothing is kept until "Apply changes" (or Save Draft) is pressed.
 *
 * Empty and zero are different: a cell nobody filled is shown and stored empty,
 * because a zero is a count of nothing and changes every percentage.
 */
export const TableGrid: React.FC<TableBlockProps> = ({
  block,
  onChange,
  reportId,
  onSaved,
  onApply,
  dirty = false,
  applying = false,
  commodity,
}) => {
  const [workbench, setWorkbench] = useState<null | 'any' | 'spreadsheet'>(null);
  const [addingColumn, setAddingColumn] = useState(false);
  const [newColumn, setNewColumn] = useState('');
  const { categories, rows, unit = 'pcs', grouping_label = 'Count / Size' } = block;
  const decimals = unit === 'kg' ? 3 : 0;
  const fmt = (n: number) => (decimals ? n.toFixed(decimals) : String(n));

  // Shown live while typing; the report recomputes these itself on render.
  const computed = useMemo(() => {
    const rowTotals: number[] = [];
    const colTotals: Record<string, number> = {};
    const colHasData: Record<string, boolean> = {};
    categories.forEach((c) => (colTotals[c.key] = 0));

    rows.forEach((row) => {
      let sum = 0;
      categories.forEach((cat) => {
        const n = toNumber(row.values?.[cat.key]);
        if (n !== null) {
          sum += n;
          colTotals[cat.key] += n;
          colHasData[cat.key] = true;
        }
      });
      rowTotals.push(sum);
    });

    const grandTotal = Object.values(colTotals).reduce((a, b) => a + b, 0);
    const colPcts: Record<string, string> = {};
    categories.forEach((cat) => {
      colPcts[cat.key] =
        grandTotal > 0 && colHasData[cat.key]
          ? ((colTotals[cat.key] / grandTotal) * 100).toFixed(2)
          : '';
    });

    return { rowTotals, colTotals, colHasData, grandTotal, colPcts };
  }, [rows, categories]);

  // ------------------------------------------------------------------ cells
  const handleCellChange = (rowIndex: number, catKey: string, raw: string) => {
    const newRows = [...rows];
    const values = { ...newRows[rowIndex].values };
    if (raw.trim() === '') {
      delete values[catKey];
    } else {
      values[catKey] = raw.trim();
    }
    newRows[rowIndex] = { ...newRows[rowIndex], values };
    onChange({ ...block, rows: newRows });
  };

  const handleGroupChange = (rowIndex: number, groupStr: string) => {
    const newRows = [...rows];
    newRows[rowIndex] = { ...newRows[rowIndex], group: groupStr };
    onChange({ ...block, rows: newRows });
  };

  // ------------------------------------------------------------------- rows
  const addRow = () => {
    onChange({ ...block, rows: [...rows, { group: '', values: {}, provenance: 'manual' }] });
  };

  const deleteRow = (idx: number) => {
    const row = rows[idx];
    const filled = Object.values(row.values || {}).filter((v) => toNumber(v) !== null).length;
    if (
      filled > 0 &&
      !window.confirm(`Remove row "${row.group || idx + 1}"? Its ${filled} figure${filled > 1 ? 's' : ''} will be deleted.`)
    ) {
      return;
    }
    onChange({ ...block, rows: rows.filter((_, i) => i !== idx) });
  };

  // ---------------------------------------------------------------- columns
  const addColumn = (raw: string) => {
    const label = columnTitle(raw);
    const key = toKey(label);
    setAddingColumn(false);
    setNewColumn('');
    if (!key) return;
    if (categories.some((c) => c.key === key)) {
      window.alert(`There is already a column called "${label}".`);
      return;
    }
    onChange({ ...block, categories: [...categories, { key, label, role: 'extra' }] });
  };

  const removeColumn = (key: string) => {
    const cat = categories.find((c) => c.key === key);
    const filled = rows.filter((r) => toNumber(r.values?.[key]) !== null).length;
    if (
      filled > 0 &&
      !window.confirm(
        `Remove the "${columnTitle(cat?.label || key)}" column?\n\n` +
          `${filled} row${filled > 1 ? 's have' : ' has'} a figure in it. Those figures will be deleted.`,
      )
    ) {
      return;
    }
    onChange({
      ...block,
      categories: categories.filter((c) => c.key !== key),
      rows: rows.map((r) => {
        const { [key]: _gone, ...rest } = r.values || {};
        return { ...r, values: rest };
      }),
    });
  };

  const headingCls =
    'py-2 px-2 whitespace-nowrap text-[11px] font-semibold text-gray-600 tracking-wide';

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4">
      <div className="flex justify-between items-center pb-3 border-b border-gray-100 gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <Table className="w-5 h-5 text-blue-600" />
          <h3 className="font-bold text-gray-800 text-lg">{block.title || 'Data Table'}</h3>
          <span className="text-xs bg-blue-50 text-blue-700 font-semibold px-2 py-0.5 rounded border border-blue-200">
            Unit: {unit}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {reportId && (
            <button
              type="button"
              onClick={() => setWorkbench('any')}
              className="flex items-center gap-1.5 text-sm bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-medium px-3 py-1.5 rounded transition border border-indigo-200"
            >
              <ScanLine className="w-4 h-4 text-indigo-600" />
              Tally Sheet
            </button>
          )}
          {/* Same workbench as Tally Sheet, opened for a spreadsheet. The old
              import behind this button read five rows and wrote zeros for any
              column it could not match, so it was replaced rather than fixed. */}
          {reportId && (
            <button
              type="button"
              onClick={() => setWorkbench('spreadsheet')}
              className="flex items-center gap-1 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium px-3 py-1.5 rounded transition"
            >
              <Upload className="w-4 h-4" />
              Import CSV / Excel
            </button>
          )}
          <button
            type="button"
            onClick={addRow}
            className="flex items-center gap-1 text-sm bg-blue-600 hover:bg-blue-700 text-white font-medium px-3 py-1.5 rounded transition"
          >
            <Plus className="w-4 h-4" />
            Add Row
          </button>
          {onApply && (
            <button
              type="button"
              onClick={() => onApply()}
              disabled={!dirty || applying}
              className={`flex items-center gap-1.5 text-sm font-semibold px-3 py-1.5 rounded transition border ${
                dirty
                  ? 'bg-emerald-600 hover:bg-emerald-700 text-white border-emerald-600'
                  : 'bg-white text-gray-400 border-gray-200 cursor-default'
              }`}
              title={dirty ? 'Save these changes to the report' : 'No unsaved changes'}
            >
              {applying ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
              {dirty ? 'Apply changes' : 'Saved'}
            </button>
          )}
        </div>
      </div>

      {/* Starting ticks come from the fruit (grapes reports have no heading
          over this table; most apple reports have no chart). Either can be
          changed for any report. */}
      <div className="flex items-center gap-6 -mt-1">
        <SectionToggle
          label={`Show the heading "${block.title || 'Condition found'}"`}
          checked={isIncluded(block.show_title)}
          onChange={(next) => onChange({ ...block, show_title: next })}
        />
        <SectionToggle
          label="Include the defect chart"
          checked={isIncluded(block.show_chart)}
          onChange={(next) => onChange({ ...block, show_chart: next })}
        />
      </div>

      <div className="overflow-x-auto">
        <table className="text-sm text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              {/* The bin and the count stay pinned while the table scrolls sideways. */}
              <th className="w-9 min-w-9 sticky left-0 z-10 bg-gray-50" />
              <th className={`${headingCls} text-left sticky left-9 z-10 bg-gray-50`}>{columnTitle(grouping_label)}</th>
              {categories.map((cat) => (
                <th key={cat.key} className={`${headingCls} text-right`}>
                  <span className="inline-flex items-center justify-end gap-1">
                    {columnTitle(cat.label)}
                    <button
                      type="button"
                      onClick={() => removeColumn(cat.key)}
                      className="text-gray-300 hover:text-red-500"
                      title={`Remove the ${columnTitle(cat.label)} column`}
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                </th>
              ))}
              <th className="py-2 px-1 align-middle">
                {addingColumn ? (
                  <input
                    autoFocus
                    value={newColumn}
                    placeholder="Column name"
                    onChange={(e) => setNewColumn(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') addColumn(newColumn);
                      if (e.key === 'Escape') {
                        setAddingColumn(false);
                        setNewColumn('');
                      }
                    }}
                    onBlur={() => (newColumn.trim() ? addColumn(newColumn) : setAddingColumn(false))}
                    className="w-28 px-1.5 py-1 border border-blue-400 rounded text-xs font-normal outline-none focus:ring-1 focus:ring-blue-500"
                  />
                ) : (
                  <button
                    type="button"
                    onClick={() => setAddingColumn(true)}
                    className="p-1 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded"
                    title="Add a column"
                  >
                    <Plus className="w-3.5 h-3.5" />
                  </button>
                )}
              </th>
              <th className={`${headingCls} text-right bg-blue-50/60 text-blue-900`}>
                Total ({unit})
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rows.map((row, rIdx) => (
              <tr key={rIdx} className="hover:bg-gray-50/60 transition">
                {/* On the left so it is always in view; at the right it sat
                    off-screen once the table was wider than the page. */}
                <td className="w-9 min-w-9 py-1 pl-1 text-center sticky left-0 z-10 bg-white">
                  <button
                    type="button"
                    onClick={() => deleteRow(rIdx)}
                    className="text-gray-300 hover:text-red-500 p-1 transition"
                    title="Remove this row"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
                <td className="py-1 px-2 sticky left-9 z-10 bg-white">
                  <input
                    type="text"
                    value={row.group}
                    placeholder="e.g. 120"
                    onChange={(e) => handleGroupChange(rIdx, e.target.value)}
                    className="w-24 px-2 py-1 border border-gray-300 rounded font-medium text-gray-800 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                  />
                </td>
                {categories.map((cat) => (
                  <td key={cat.key} className="py-1 px-1 text-right">
                    <input
                      type="number"
                      step={unit === 'kg' ? '0.001' : '1'}
                      value={row.values?.[cat.key] ?? ''}
                      onChange={(e) => handleCellChange(rIdx, cat.key, e.target.value)}
                      className="w-16 text-right px-2 py-1 border border-gray-300 rounded text-gray-800 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                    />
                  </td>
                ))}
                <td />
                <td className="py-1 px-3 text-right font-mono font-semibold bg-blue-50/30 text-blue-800 select-none whitespace-nowrap">
                  {fmt(computed.rowTotals[rIdx] ?? 0)}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="bg-gray-100 font-bold border-t-2 border-gray-300 text-gray-900">
              <td className="sticky left-0 z-10 bg-gray-100" />
              <td className="py-2 px-2 whitespace-nowrap sticky left-9 z-10 bg-gray-100">Total</td>
              {categories.map((cat) => (
                <td key={cat.key} className="py-2 px-2 text-right font-mono whitespace-nowrap">
                  {computed.colHasData[cat.key] ? fmt(computed.colTotals[cat.key]) : ''}
                </td>
              ))}
              <td />
              <td className="py-2 px-3 text-right font-mono bg-blue-100/50 text-blue-950 whitespace-nowrap">
                {fmt(computed.grandTotal)}
              </td>
            </tr>
            <tr className="bg-gray-50 text-xs text-gray-600 font-mono font-medium">
              <td className="sticky left-0 z-10 bg-gray-50" />
              <td className="py-1.5 px-2 font-semibold sticky left-9 z-10 bg-gray-50">%</td>
              {categories.map((cat) => (
                <td key={cat.key} className="py-1.5 px-2 text-right whitespace-nowrap">
                  {computed.colPcts[cat.key] ? `${computed.colPcts[cat.key]}%` : ''}
                </td>
              ))}
              <td />
              <td className="py-1.5 px-3 text-right font-bold text-gray-800 bg-blue-50/50 whitespace-nowrap">
                {computed.grandTotal > 0 ? '100.00%' : ''}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
      <p className="text-xs text-gray-400 italic">
        Totals and percentages are worked out from the figures and cannot be typed over. Columns
        left empty in every row are not printed in the report.
      </p>

      {reportId && (
        <VerificationWorkbench
          reportId={reportId}
          isOpen={workbench !== null}
          onClose={() => setWorkbench(null)}
          blockId={block.id}
          commodity={commodity}
          sourceHint={workbench === 'spreadsheet' ? 'spreadsheet' : 'any'}
          existing={rows.length ? { categories, rows, unit } : undefined}
          onSuccess={(updatedBlockState, version) => {
            if (onSaved) {
              onSaved(updatedBlockState, version);
            } else {
              const tbl = updatedBlockState.blocks?.find((b: any) => b.id === block.id);
              if (tbl) onChange(tbl);
            }
          }}
        />
      )}
    </div>
  );
};

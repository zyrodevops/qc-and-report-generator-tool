import React, { useMemo, useState } from 'react';
import { Table, Upload, Plus, Trash2, ScanLine } from 'lucide-react';
import { VerificationWorkbench } from './VerificationWorkbench';

interface Category {
  key: string;
  label: string;
}

interface TableRow {
  group: string;
  boxes_opened?: number;
  values: Record<string, number | string>;
}

interface TableBlockProps {
  block: {
    id: string;
    title?: string;
    unit?: string;
    grouping_label?: string;
    categories: Category[];
    rows: TableRow[];
  };
  onChange: (updatedBlock: any) => void;
  onImportCsv?: () => void;
  reportId?: string;
  onBlockStateChange?: (updatedBlockState: any) => void;
  /** Decides which defect columns the tally grid offers. */
  commodity?: string;
}

export const TableGrid: React.FC<TableBlockProps> = ({
  block,
  onChange,
  onImportCsv,
  reportId,
  onBlockStateChange,
  commodity,
}) => {
  const [isOcrOpen, setIsOcrOpen] = useState(false);
  const { categories, rows, unit = 'pcs', grouping_label = 'Group' } = block;

  // Live in-browser computation: locked computed cells that cannot be typed over
  const computed = useMemo(() => {
    const rowTotals: number[] = [];
    const rowPcts: number[][] = [];
    const colTotals: Record<string, number> = {};
    categories.forEach((c) => (colTotals[c.key] = 0));

    rows.forEach((row) => {
      let rSum = 0;
      const cVals: number[] = [];
      categories.forEach((cat) => {
        const val = parseFloat(String(row.values[cat.key] || 0)) || 0;
        cVals.push(val);
        rSum += val;
        colTotals[cat.key] += val;
      });
      rowTotals.push(rSum);

      if (rSum > 0) {
        rowPcts.push(cVals.map((v) => Math.round((v / rSum) * 10000) / 100));
      } else {
        rowPcts.push(categories.map(() => 0));
      }
    });

    const grandTotal = Object.values(colTotals).reduce((a, b) => a + b, 0);
    const colPcts: Record<string, number> = {};
    categories.forEach((cat) => {
      colPcts[cat.key] = grandTotal > 0 ? Math.round((colTotals[cat.key] / grandTotal) * 10000) / 100 : 0;
    });

    return { rowTotals, rowPcts, colTotals, grandTotal, colPcts };
  }, [rows, categories]);

  const handleCellChange = (rowIndex: number, catKey: string, valStr: string) => {
    const num = parseFloat(valStr) || 0;
    const newRows = [...rows];
    newRows[rowIndex] = {
      ...newRows[rowIndex],
      values: {
        ...newRows[rowIndex].values,
        [catKey]: num,
      },
    };
    onChange({ ...block, rows: newRows });
  };

  const handleGroupChange = (rowIndex: number, groupStr: string) => {
    const newRows = [...rows];
    newRows[rowIndex] = { ...newRows[rowIndex], group: groupStr };
    onChange({ ...block, rows: newRows });
  };

  const addRow = () => {
    const emptyVals: Record<string, number> = {};
    categories.forEach((c) => (emptyVals[c.key] = 0));
    const newRow: TableRow = {
      group: `Sample ${rows.length + 1}`,
      values: emptyVals,
    };
    onChange({ ...block, rows: [...rows, newRow] });
  };

  const deleteRow = (idx: number) => {
    const newRows = rows.filter((_, i) => i !== idx);
    onChange({ ...block, rows: newRows });
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4">
      <div className="flex justify-between items-center pb-3 border-b border-gray-100">
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
              onClick={() => setIsOcrOpen(true)}
              className="flex items-center gap-1.5 text-sm bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-medium px-3 py-1.5 rounded transition border border-indigo-200"
            >
              <ScanLine className="w-4 h-4 text-indigo-600" />
              Tally Sheet
            </button>
          )}
          {onImportCsv && (
            <button
              type="button"
              onClick={onImportCsv}
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
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-600 uppercase">
              <th className="py-2.5 px-3">{grouping_label}</th>
              {categories.map((cat) => (
                <th key={cat.key} className="py-2.5 px-3 text-right">
                  {cat.label}
                </th>
              ))}
              <th className="py-2.5 px-3 text-right bg-blue-50/50 text-blue-900">Total ({unit})</th>
              <th className="py-2.5 px-3 text-right bg-blue-50/50 text-blue-900">%</th>
              <th className="py-2.5 px-2 w-8"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {rows.map((row, rIdx) => (
              <tr key={rIdx} className="hover:bg-gray-50/60 transition">
                <td className="py-2 px-3">
                  <input
                    type="text"
                    value={row.group}
                    onChange={(e) => handleGroupChange(rIdx, e.target.value)}
                    className="w-full px-2 py-1 border border-gray-300 rounded font-medium text-gray-800 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                  />
                </td>
                {categories.map((cat) => (
                  <td key={cat.key} className="py-2 px-2 text-right">
                    <input
                      type="number"
                      step={unit === 'kg' ? '0.001' : '1'}
                      value={row.values[cat.key] ?? 0}
                      onChange={(e) => handleCellChange(rIdx, cat.key, e.target.value)}
                      className="w-24 text-right px-2 py-1 border border-gray-300 rounded text-gray-800 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                    />
                  </td>
                ))}
                {/* LOCKED COMPUTED CELL */}
                <td className="py-2 px-3 text-right font-mono font-semibold bg-blue-50/30 text-blue-800 select-none">
                  {unit === 'kg' ? computed.rowTotals[rIdx].toFixed(3) : computed.rowTotals[rIdx]}
                </td>
                {/* LOCKED COMPUTED PERCENTAGES */}
                <td className="py-2 px-3 text-right font-mono text-xs text-gray-600 bg-blue-50/30 select-none">
                  {computed.rowPcts[rIdx]?.join(' / ') || '0%'}
                </td>
                <td className="py-2 px-1 text-center">
                  <button
                    type="button"
                    onClick={() => deleteRow(rIdx)}
                    className="text-gray-400 hover:text-red-500 p-1 transition"
                    title="Delete row"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            {/* COLUMN TOTALS ROW */}
            <tr className="bg-gray-100 font-bold border-t-2 border-gray-300 text-gray-900">
              <td className="py-2.5 px-3">Total</td>
              {categories.map((cat) => (
                <td key={cat.key} className="py-2.5 px-3 text-right font-mono">
                  {unit === 'kg' ? computed.colTotals[cat.key].toFixed(3) : computed.colTotals[cat.key]}
                </td>
              ))}
              <td className="py-2.5 px-3 text-right font-mono bg-blue-100/50 text-blue-950">
                {unit === 'kg' ? computed.grandTotal.toFixed(3) : computed.grandTotal}
              </td>
              <td className="py-2.5 px-3 text-right bg-blue-100/50"></td>
              <td></td>
            </tr>
            {/* COLUMN PERCENTAGES ROW */}
            <tr className="bg-gray-50 text-xs text-gray-600 font-mono font-medium">
              <td className="py-2 px-3 font-semibold">%</td>
              {categories.map((cat) => (
                <td key={cat.key} className="py-2 px-3 text-right">
                  {computed.colPcts[cat.key]}%
                </td>
              ))}
              <td className="py-2 px-3 text-right font-bold text-gray-800 bg-blue-50/50">100.00%</td>
              <td className="bg-blue-50/50"></td>
              <td></td>
            </tr>
          </tfoot>
        </table>
      </div>
      <p className="text-xs text-gray-400 italic">
        * Computed totals and percentages are calculated dynamically and cannot be directly typed over.
      </p>

      {reportId && (
        <VerificationWorkbench
          reportId={reportId}
          isOpen={isOcrOpen}
          onClose={() => setIsOcrOpen(false)}
          blockId={block.id}
          commodity={commodity}
          onSuccess={(updatedBlockState) => {
            if (onBlockStateChange) {
              onBlockStateChange(updatedBlockState);
            } else {
              const tbl = updatedBlockState.blocks?.find((b: any) => b.type === 'table');
              if (tbl) onChange(tbl);
            }
          }}
        />
      )}
    </div>
  );
};


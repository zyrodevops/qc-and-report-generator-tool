import React from 'react';
import { computeTable, computeTableSummary } from '../compute';
import { columnTitle } from '../../../utils/labels';
import { chartBars, chartTitle } from '../../../utils/findings';
import { FindingsChart } from './FindingsChart';

export interface TableBlockProps {
  block: any;
  computed?: any;
  onChange?: (updatedBlock: any) => void;
  editable?: boolean;
}

export const TableBlock: React.FC<TableBlockProps> = ({
  block,
  computed,
  onChange,
  editable = true,
}) => {
  const allCategories: any[] = block?.categories || [];
  const rows: any[] = block?.rows || [];

  // Same rule as backend/app/render/table_columns.py, so the preview shows the
  // columns the downloaded report will: a column appears when at least one row
  // has a value in it. Zero counts as a value; only an all-blank column is
  // left out. The original index is kept because per-row percentages are
  // positional against the full list.
  const hasValue = (v: any) => v !== null && v !== undefined && String(v).trim() !== '';
  const shownWithIdx = allCategories
    .map((c, i) => ({ c, i }))
    .filter(({ c }) => rows.length === 0 || rows.some((r) => hasValue(r?.values?.[c.key])));
  const visible = shownWithIdx.length ? shownWithIdx : allCategories.map((c, i) => ({ c, i }));
  const categories: any[] = visible.map((v) => v.c);
  const origIdx: number[] = visible.map((v) => v.i);
  const unit = block?.unit || 'pcs';
  const title = block?.title || 'DEFECT ANALYSIS BREAKDOWN';
  const groupLabel = block?.grouping_label || 'Group';
  // Optional Container column, same rule as table_columns.shows_container:
  // ticked, and at least one row names a container.
  const withCont = Boolean(block?.show_container) && rows.some((r) => hasValue(r?.container));
  const contTh = (cls: string) =>
    withCont ? <th className={`border border-slate-400 ${cls} text-left`}>Container</th> : null;
  const contTd = (cls: string, row?: any) =>
    withCont ? (
      <td className={`border border-slate-400 ${cls} font-mono whitespace-nowrap`}>{row?.container ?? ''}</td>
    ) : null;

  const handleGroupChange = (rIdx: number, val: string) => {
    if (!onChange) return;
    const newRows = [...rows];
    newRows[rIdx] = { ...newRows[rIdx], group: val };
    onChange({ ...block, rows: newRows });
  };

  const handleCellChange = (rIdx: number, catKey: string, val: string) => {
    if (!onChange) return;
    const newRows = [...rows];
    const newValues = { ...(newRows[rIdx]?.values || {}) };
    newValues[catKey] = val;
    newRows[rIdx] = { ...newRows[rIdx], values: newValues };
    onChange({ ...block, rows: newRows });
  };

  // Fallback to client compute if computed is not passed
  const calc = computed || computeTable(block);
  const rowTotals = calc?.row_totals || [];
  const rowPcts = calc?.row_percentages || [];
  const colTotals = calc?.column_totals || {};
  const grandTotal = calc?.grand_total || '';
  const colPcts = calc?.column_percentages || {};

  // The graph (see utils/findings.ts) and the FINAL SUMMARY, as the Word file.
  const bars = chartBars(block, calc, categories.map((c) => c.key));
  const summary = calc?.summary || computeTableSummary(block);
  const showSummary = Boolean(summary && summary.groups.length >= 2);
  const pctText = (v: any) => (String(v ?? '') !== '' ? `${v}%` : '');
  const boxes = (n: number) => (n === 1 ? '1 Box' : `${n} Boxes`);

  const isTwoTier = block?.layout === 'two_tier' && rowPcts.length > 0;

  return (
    <div className="table-block my-3">
      {block?.show_title !== false && (
      <div className="flex justify-between items-center border-b border-slate-300 pb-1 mb-2">
        <h2 className="text-[12px] font-bold text-[#00387A] uppercase tracking-wider">
          {title}
        </h2>
        <span className="text-[11px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded border border-slate-200 uppercase font-mono">
          Unit: {unit}
        </span>
      </div>
      )}

      {isTwoTier ? (
        <table className="w-full border-collapse border border-slate-400 text-xs">
          <thead>
            <tr className="bg-slate-100 text-slate-800 font-bold border-b border-slate-400">
              <th className="border border-slate-400 px-2.5 py-1.5 text-left">{columnTitle(groupLabel)}</th>
              {contTh('px-2.5 py-1.5')}
              {categories.map((c) => (
                <th key={c.key} className="border border-slate-400 px-2 py-1.5 text-right">
                  {columnTitle(c.label)}
                </th>
              ))}
              <th className="border border-slate-400 px-2.5 py-1.5 text-right font-bold">
                Total ({unit})
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rIdx) => {
              const rowSum = rowTotals[rIdx] ?? '';
              const rowPct = rowPcts[rIdx] || [];

              return (
                <React.Fragment key={rIdx}>
                  {/* Pieces Count Row */}
                  <tr className="border-b border-slate-200 hover:bg-slate-50/50">
                    <td className="border border-slate-400 p-0 font-bold text-slate-900 bg-slate-50/40">
                      {editable && onChange ? (
                        <input
                          type="text"
                          value={row.group}
                          onChange={(e) => handleGroupChange(rIdx, e.target.value)}
                          className="w-full bg-transparent px-2.5 py-1.5 border-none outline-none hover:bg-blue-50/40 focus:bg-white focus:ring-1 focus:ring-blue-500 font-bold text-xs text-slate-900 transition-colors"
                        />
                      ) : (
                        <div className="px-2.5 py-1.5">{row.group}</div>
                      )}
                    </td>
                    {contTd('px-2.5 py-1.5', row)}
                    {categories.map((c) => (
                      <td
                        key={c.key}
                        className="border border-slate-400 p-0 text-right font-mono text-slate-800"
                      >
                        {editable && onChange ? (
                          <input
                            type="text"
                            value={row.values?.[c.key] ?? ''}
                            onChange={(e) => handleCellChange(rIdx, c.key, e.target.value)}
                            className="w-full bg-transparent px-2 py-1.5 text-right font-mono border-none outline-none hover:bg-blue-50/40 focus:bg-white focus:ring-1 focus:ring-blue-500 text-xs text-slate-800 transition-colors"
                          />
                        ) : (
                          <div className="px-2 py-1.5">{row.values?.[c.key] ?? ''}</div>
                        )}
                      </td>
                    ))}
                    <td className="border border-slate-400 px-2.5 py-1.5 text-right font-mono font-bold text-[#00387A] bg-blue-50/30">
                      {rowSum}
                    </td>
                  </tr>

                  {/* Percentage Row */}
                  <tr className="border-b border-slate-300 bg-slate-50/60 text-slate-600">
                    <td className="border border-slate-400 px-2.5 py-1 text-slate-500 italic text-[11px]">
                      Percentage
                    </td>
                    {contTd('px-2.5 py-1')}
                    {categories.map((c, cIdx) => (
                      <td
                        key={c.key}
                        className="border border-slate-400 px-2 py-1 text-right font-mono text-[11px] text-slate-700"
                      >
                        {rowPct[origIdx[cIdx]] ? `${rowPct[origIdx[cIdx]]}%` : ''}
                      </td>
                    ))}
                    <td className="border border-slate-400 px-2.5 py-1 text-right font-mono font-bold text-[11px] text-slate-800">
                      100.00%
                    </td>
                  </tr>
                </React.Fragment>
              );
            })}

            {/* Total Pieces Row */}
            <tr className="bg-slate-100 font-bold text-slate-900 border-t-2 border-slate-400">
              <td className="border border-slate-400 px-2.5 py-1.5 font-bold">Total ({unit})</td>
              {contTd('px-2.5 py-1.5')}
              {categories.map((c) => (
                <td
                  key={c.key}
                  className="border border-slate-400 px-2 py-1.5 text-right font-mono font-bold text-slate-900"
                >
                  {colTotals[c.key] ?? ''}
                </td>
              ))}
              <td className="border border-slate-400 px-2.5 py-1.5 text-right font-mono font-black text-[#00387A] bg-blue-100/50">
                {grandTotal}
              </td>
            </tr>

            {/* Total Percentage Row */}
            <tr className="bg-slate-50 font-bold text-slate-800 border-b border-slate-400">
              <td className="border border-slate-400 px-2.5 py-1.5 font-bold">Percentage</td>
              {contTd('px-2.5 py-1.5')}
              {categories.map((c) => (
                <td
                  key={c.key}
                  className="border border-slate-400 px-2 py-1.5 text-right font-mono text-[11px] text-slate-800"
                >
                  {colPcts[c.key] ? `${colPcts[c.key]}%` : ''}
                </td>
              ))}
              <td className="border border-slate-400 px-2.5 py-1.5 text-right font-mono font-bold text-slate-900">
                100.00%
              </td>
            </tr>
          </tbody>
        </table>
      ) : (
        <table
          className="w-full border-collapse border border-slate-400"
          // Headings may wrap between words but never inside one ("Shrivelle/d"),
          // so the size steps down as the column count goes up instead.
          style={{ fontSize: categories.length > 11 ? '8px' : categories.length > 8 ? '9px' : '10px' }}
        >
          <thead>
            <tr className="bg-slate-100 text-slate-800 font-bold border-b border-slate-400">
              <th className="border border-slate-400 px-1 py-1 text-left align-bottom leading-tight">
                {columnTitle(groupLabel)}
              </th>
              {contTh('px-1 py-1 align-bottom leading-tight')}
              {categories.map((c) => (
                <th
                  key={c.key}
                  className="border border-slate-400 px-1 py-1 text-center align-bottom leading-tight"
                  style={{ wordBreak: 'normal', overflowWrap: 'normal', hyphens: 'manual' }}
                >
                  {columnTitle(c.label)}
                </th>
              ))}
              <th className="border border-slate-400 px-1 py-1 text-center align-bottom font-bold leading-tight">
                Total ({unit})
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rIdx) => {
              const rowSum = rowTotals[rIdx] ?? '';

              return (
                <tr key={rIdx} className="border-b border-slate-300 hover:bg-slate-50/50">
                  <td className="border border-slate-400 p-0 font-medium text-slate-800">
                    {editable && onChange ? (
                      <input
                        type="text"
                        value={row.group}
                        onChange={(e) => handleGroupChange(rIdx, e.target.value)}
                        size={1}
                        className="w-full min-w-0 bg-transparent px-1 py-1 border-none outline-none hover:bg-blue-50/40 focus:bg-white focus:ring-1 focus:ring-blue-500 font-medium text-[1em] text-slate-800 transition-colors"
                      />
                    ) : (
                      <div className="px-1 py-1">{row.group}</div>
                    )}
                  </td>
                  {contTd('px-1 py-1', row)}
                  {categories.map((c) => (
                    <td
                      key={c.key}
                      className="border border-slate-400 p-0 text-right font-mono text-slate-700"
                    >
                      {editable && onChange ? (
                        <input
                          type="text"
                          value={row.values?.[c.key] ?? ''}
                          onChange={(e) => handleCellChange(rIdx, c.key, e.target.value)}
                          size={1}
                          className="w-full min-w-0 bg-transparent px-1 py-1 text-right font-mono border-none outline-none hover:bg-blue-50/40 focus:bg-white focus:ring-1 focus:ring-blue-500 text-[1em] text-slate-700 transition-colors"
                        />
                      ) : (
                        <div className="px-1 py-1">{row.values?.[c.key] ?? ''}</div>
                      )}
                    </td>
                  ))}
                  <td className="border border-slate-400 px-1 py-1 text-right font-mono font-bold text-[#00387A] bg-blue-50/30 whitespace-nowrap">
                    {rowSum}
                  </td>
                </tr>
              );
            })}

            {/* Column Totals Row */}
            <tr className="bg-slate-100 font-bold text-slate-900 border-t-2 border-slate-400">
              <td className="border border-slate-400 px-1 py-1 font-bold">Total</td>
              {contTd('px-1 py-1')}
              {categories.map((c) => (
                <td
                  key={c.key}
                  className="border border-slate-400 px-1 py-1 text-right font-mono font-bold text-slate-900 whitespace-nowrap"
                >
                  {colTotals[c.key] ?? ''}
                </td>
              ))}
              <td className="border border-slate-400 px-1 py-1 text-right font-mono font-black text-[#00387A] bg-blue-100/50 whitespace-nowrap">
                {grandTotal}
              </td>
            </tr>

            {/* Column Percentages Row */}
            <tr className="bg-slate-50 font-semibold text-slate-800">
              <td className="border border-slate-400 px-1 py-1 font-bold">%</td>
              {contTd('px-1 py-1')}
              {categories.map((c) => (
                <td
                  key={c.key}
                  className="border border-slate-400 px-1 py-1 text-right font-mono text-slate-700 whitespace-nowrap"
                >
                  {colPcts[c.key] ? `${colPcts[c.key]}%` : ''}
                </td>
              ))}
              <td className="border border-slate-400 px-1 py-1 text-right font-mono font-bold text-slate-900 whitespace-nowrap">
                100.00%
              </td>
            </tr>
          </tbody>
        </table>
      )}

      {/* FINAL SUMMARY: each group's totals, then the table's */}
      {showSummary && summary && (
        <div className="my-3">
          <p className="text-[11px] font-bold underline mb-1">{block?.summary?.title || 'FINAL SUMMARY'}</p>
          <table className="w-full border-collapse border border-slate-400 text-[9px] summary-table">
            <thead>
              <tr className="bg-slate-100 font-bold">
                <th className="border border-slate-400 px-1 py-1 text-left">
                  {summary.by === 'container' ? 'Container' : columnTitle(groupLabel)}
                </th>
                {categories.map((c) => (
                  <th key={c.key} className="border border-slate-400 px-1 py-1 text-center">{columnTitle(c.label)}</th>
                ))}
                <th className="border border-slate-400 px-1 py-1 text-center">Total ({unit})</th>
              </tr>
            </thead>
            <tbody>
              {summary.groups.map((g: any, i: number) => (
                <React.Fragment key={i}>
                  <tr>
                    <td className="border border-slate-400 px-1 py-1">{g.key ? `${g.key} (${boxes(g.boxes)})` : `(${boxes(g.boxes)})`}</td>
                    {categories.map((c) => (
                      <td key={c.key} className="border border-slate-400 px-1 py-1 text-right font-mono">{g.column_totals[c.key] ?? ''}</td>
                    ))}
                    <td className="border border-slate-400 px-1 py-1 text-right font-mono">{g.grand_total}</td>
                  </tr>
                  <tr className="bg-slate-50 text-slate-700">
                    <td className="border border-slate-400 px-1 py-1 italic">Percentage</td>
                    {categories.map((c) => (
                      <td key={c.key} className="border border-slate-400 px-1 py-1 text-right font-mono">{pctText(g.column_percentages[c.key])}</td>
                    ))}
                    <td className="border border-slate-400 px-1 py-1 text-right font-mono">100.00%</td>
                  </tr>
                </React.Fragment>
              ))}
              <tr className="bg-slate-100 font-bold">
                <td className="border border-slate-400 px-1 py-1">Total {boxes(summary.boxes)}</td>
                {categories.map((c) => (
                  <td key={c.key} className="border border-slate-400 px-1 py-1 text-right font-mono">{colTotals[c.key] ?? ''}</td>
                ))}
                <td className="border border-slate-400 px-1 py-1 text-right font-mono">{grandTotal}</td>
              </tr>
              <tr className="bg-slate-50 font-bold">
                <td className="border border-slate-400 px-1 py-1">Percentage</td>
                {categories.map((c) => (
                  <td key={c.key} className="border border-slate-400 px-1 py-1 text-right font-mono">{pctText(colPcts[c.key])}</td>
                ))}
                <td className="border border-slate-400 px-1 py-1 text-right font-mono">100.00%</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {/* The graph, as the client draws it */}
      {block?.show_chart !== false && bars.length > 0 && <FindingsChart bars={bars} title={chartTitle(block)} />}
    </div>
  );
};

import React from 'react';
import { computeTable } from '../compute';
import { columnTitle } from '../../../utils/labels';

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

  // Donut chart slices calculation
  const colors = ['#2563eb', '#f59e0b', '#ef4444', '#8b5cf6', '#10b981', '#64748b'];
  const chartItems: { label: string; pct: number; color: string }[] = [];
  allCategories.forEach((cat, idx) => {
    const p = parseFloat(String(colPcts[cat.key] || 0));
    if (p > 0) {
      chartItems.push({
        label: cat.label.replace(/\(.*\)/, '').trim(),
        pct: p,
        color: colors[idx % colors.length],
      });
    }
  });

  // Calculate SVG donut paths
  let cumulativeAngle = 0;
  const radius = 60;
  const innerRadius = 36;
  const cx = 80;
  const cy = 80;

  const slices = chartItems.map((item) => {
    const angle = (item.pct / 100) * 360;
    const startAngle = cumulativeAngle;
    const endAngle = cumulativeAngle + angle;
    cumulativeAngle += angle;

    const startRad = ((startAngle - 90) * Math.PI) / 180;
    const endRad = ((endAngle - 90) * Math.PI) / 180;

    const x1 = cx + radius * Math.cos(startRad);
    const y1 = cy + radius * Math.sin(startRad);
    const x2 = cx + radius * Math.cos(endRad);
    const y2 = cy + radius * Math.sin(endRad);

    const x3 = cx + innerRadius * Math.cos(endRad);
    const y3 = cy + innerRadius * Math.sin(endRad);
    const x4 = cx + innerRadius * Math.cos(startRad);
    const y4 = cy + innerRadius * Math.sin(startRad);

    const largeArc = angle > 180 ? 1 : 0;

    const pathData = `M ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} L ${x3} ${y3} A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${x4} ${y4} Z`;

    return {
      ...item,
      path: pathData,
    };
  });

  const isTwoTier = block?.layout === 'two_tier' && rowPcts.length > 0;

  return (
    <div className="table-block my-3">
      <div className="flex justify-between items-center border-b border-slate-300 pb-1 mb-2">
        <h2 className="text-[12px] font-bold text-[#00387A] uppercase tracking-wider">
          {title}
        </h2>
        <span className="text-[11px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded border border-slate-200 uppercase font-mono">
          Unit: {unit}
        </span>
      </div>

      {isTwoTier ? (
        <table className="w-full border-collapse border border-slate-400 text-xs">
          <thead>
            <tr className="bg-slate-100 text-slate-800 font-bold border-b border-slate-400">
              <th className="border border-slate-400 px-2.5 py-1.5 text-left">{columnTitle(groupLabel)}</th>
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

      {/* Embedded Donut Chart */}
      {chartItems.length > 0 && (
        <div className="flex flex-col items-center justify-center my-4 p-3 bg-white rounded border border-slate-200">
          <div className="flex items-center gap-6">
            <svg width="160" height="160" viewBox="0 0 160 160" className="drop-shadow-xs">
              {slices.map((s, i) => (
                <path
                  key={i}
                  d={s.path}
                  fill={s.color}
                  stroke="#ffffff"
                  strokeWidth="1.5"
                />
              ))}
              <circle cx={cx} cy={cy} r={innerRadius} fill="#ffffff" />
              <text
                x={cx}
                y={cy - 4}
                textAnchor="middle"
                fontSize="11"
                fontWeight="bold"
                fill="#00387A"
              >
                {grandTotal}
              </text>
              <text
                x={cx}
                y={cy + 10}
                textAnchor="middle"
                fontSize="8"
                fill="#64748b"
                fontWeight="500"
              >
                {unit.toUpperCase()}
              </text>
            </svg>

            {/* Legend */}
            <div className="grid grid-cols-1 gap-1 text-xs">
              {slices.map((s, i) => (
                <div key={i} className="flex items-center gap-2">
                  <span
                    className="w-2.5 h-2.5 rounded-full inline-block shrink-0"
                    style={{ backgroundColor: s.color }}
                  />
                  <span className="font-medium text-slate-700 text-[11px]">
                    {s.label}:
                  </span>
                  <span className="font-mono font-bold text-slate-900 text-[11px]">
                    {s.pct.toFixed(2)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
          <p className="text-[10px] italic text-slate-500 mt-2">
            Chart: {title || 'Quality Analysis Breakdown'}
          </p>
        </div>
      )}
    </div>
  );
};

import React from 'react';
import { computeTable } from '../compute';

export interface TableBlockProps {
  block: any;
  computed?: any;
}

export const TableBlock: React.FC<TableBlockProps> = ({ block, computed }) => {
  const categories: any[] = block?.categories || [];
  const rows: any[] = block?.rows || [];
  const unit = block?.unit || 'pcs';
  const title = block?.title || 'DEFECT ANALYSIS BREAKDOWN';
  const groupLabel = block?.grouping_label || 'Group';

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
  categories.forEach((cat, idx) => {
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

      <table className="w-full border-collapse border border-slate-400 text-xs">
        <thead>
          <tr className="bg-slate-100 text-slate-800 font-bold border-b border-slate-400">
            <th className="border border-slate-400 px-2.5 py-1.5 text-left">{groupLabel}</th>
            {categories.map((c) => (
              <th key={c.key} className="border border-slate-400 px-2 py-1.5 text-right">
                {c.label}
              </th>
            ))}
            <th className="border border-slate-400 px-2.5 py-1.5 text-right font-bold">
              Total ({unit})
            </th>
            <th className="border border-slate-400 px-2 py-1.5 text-center">%</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rIdx) => {
            const rowSum = rowTotals[rIdx] ?? '';
            const rowPct = rowPcts[rIdx] ? rowPcts[rIdx].join(' / ') : '';

            return (
              <tr key={rIdx} className="border-b border-slate-300 hover:bg-slate-50/50">
                <td className="border border-slate-400 px-2.5 py-1.5 font-medium text-slate-800">
                  {row.group}
                </td>
                {categories.map((c) => (
                  <td
                    key={c.key}
                    className="border border-slate-400 px-2 py-1.5 text-right font-mono text-slate-700"
                  >
                    {row.values?.[c.key] ?? ''}
                  </td>
                ))}
                <td className="border border-slate-400 px-2.5 py-1.5 text-right font-mono font-bold text-[#00387A] bg-blue-50/30">
                  {rowSum}
                </td>
                <td className="border border-slate-400 px-2 py-1.5 text-center font-mono text-[11px] text-slate-600 bg-slate-50/50">
                  {rowPct}
                </td>
              </tr>
            );
          })}

          {/* Column Totals Row */}
          <tr className="bg-slate-100 font-bold text-slate-900 border-t-2 border-slate-400">
            <td className="border border-slate-400 px-2.5 py-1.5 font-bold">Total</td>
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
            <td className="border border-slate-400 px-2 py-1.5"></td>
          </tr>

          {/* Column Percentages Row */}
          <tr className="bg-slate-50 font-semibold text-slate-800">
            <td className="border border-slate-400 px-2.5 py-1.5 font-bold">%</td>
            {categories.map((c) => (
              <td
                key={c.key}
                className="border border-slate-400 px-2 py-1.5 text-right font-mono text-[11px] text-slate-700"
              >
                {colPcts[c.key] ? `${colPcts[c.key]}%` : ''}
              </td>
            ))}
            <td className="border border-slate-400 px-2.5 py-1.5 text-right font-mono font-bold text-slate-900">
              100.00%
            </td>
            <td className="border border-slate-400 px-2 py-1.5"></td>
          </tr>
        </tbody>
      </table>

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

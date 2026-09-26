import React from 'react';
import { Bar } from '../../../utils/findings';

/** The client's column chart: % axis, a column per condition, Total at 100%, title underneath. */
export const FindingsChart: React.FC<{ bars: Bar[]; title: string }> = ({ bars, title }) => {
  if (!bars.length) return null;
  const W = 600;
  const left = 52;
  const right = 10;
  const top = 14;
  const plotH = 190;
  const base = top + plotH;
  const slot = (W - left - right) / bars.length;
  const barW = slot * 0.6;
  const y = (pct: number) => base - (Math.min(pct, 110) / 110) * plotH;
  const ticks = Array.from({ length: 11 }, (_, i) => i * 10);

  // Narrower wrapping and smaller text as the columns get more (as in Word).
  const n = bars.length;
  const width = n <= 7 ? 16 : n <= 10 ? 12 : 9;
  const labelSize = n <= 7 ? 8 : n <= 10 ? 7 : 6;
  const wrap = (name: string) => {
    const words = name.split(/\s+/);
    const lines: string[] = [];
    let cur = '';
    words.forEach((w) => {
      if ((cur + ' ' + w).trim().length > width && cur) {
        lines.push(cur);
        cur = w;
      } else cur = (cur + ' ' + w).trim();
    });
    if (cur) lines.push(cur);
    return lines;
  };
  // The title sits just under the longest label, as in the Word file.
  const maxLines = Math.max(...bars.map((b) => wrap(b.name).length + 1));
  const titleY = base + 13 + maxLines * 10 + 14;
  const H = titleY + 6;

  return (
    <div className="findings-chart my-3 flex justify-center">
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ maxWidth: '16cm' }} role="img" aria-label={title}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={left} x2={W - right} y1={y(t)} y2={y(t)} stroke="#D9D9D9" strokeWidth={0.6} />
            <text x={left - 6} y={y(t) + 3} fontSize={8} textAnchor="end" fill="#000">
              {t.toFixed(2)}%
            </text>
          </g>
        ))}
        <line x1={left} x2={left} y1={top} y2={base} stroke="#BFBFBF" />
        <line x1={left} x2={W - right} y1={base} y2={base} stroke="#BFBFBF" />
        {bars.map((b, i) => {
          const cx = left + slot * i + slot / 2;
          const lines = [...wrap(b.name), `(${b.qty})`];
          return (
            <g key={i}>
              <rect x={cx - barW / 2} y={y(b.pct)} width={barW} height={base - y(b.pct)} fill={b.colour} stroke="#404040" strokeWidth={0.5} />
              <text x={cx} y={y(b.pct) - 4} fontSize={9} fontWeight="bold" textAnchor="middle" fill="#000">
                {b.pct.toFixed(2)}%
              </text>
              {lines.map((l, j) => (
                <text key={j} x={cx} y={base + 13 + j * 10} fontSize={labelSize} textAnchor="middle" fill="#000">
                  {l}
                </text>
              ))}
            </g>
          );
        })}
        <text x={W / 2} y={titleY} fontSize={11} fontWeight="bold" textAnchor="middle" fill="#000">
          {title}
        </text>
      </svg>
    </div>
  );
};

export default FindingsChart;

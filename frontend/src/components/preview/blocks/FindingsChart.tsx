import React from 'react';
import { Bar } from '../../../utils/findings';

/** The client's column chart: dark background, top underlined title, % axis, condition columns, Total at 100%. */
export const FindingsChart: React.FC<{ bars: Bar[]; title: string }> = ({ bars, title }) => {
  if (!bars.length) return null;
  const W = 600;
  const left = 54;
  const right = 16;
  const top = 46;
  const plotH = 175;
  const base = top + plotH;
  const slot = (W - left - right) / bars.length;
  const barW = slot * 0.55;
  const y = (pct: number) => base - (Math.min(pct, 115) / 115) * plotH;
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

  const maxLines = Math.max(...bars.map((b) => wrap(b.name).length + 1));
  const H = base + 14 + maxLines * 10 + 10;
  const displayTitle = (title || 'SURVEY FINDINGS IN GRAPH').toUpperCase();

  return (
    <div className="findings-chart my-3 flex justify-center">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        style={{ maxWidth: '16cm', height: 'auto', display: 'block' }}
        role="img"
        aria-label={displayTitle}
      >
        {/* Dark card background */}
        <rect width="100%" height="100%" fill="#262626" rx="4" />

        {/* Title at TOP with underline */}
        <text
          x={W / 2}
          y={26}
          fontSize={12}
          fontWeight="bold"
          textAnchor="middle"
          fill="#FFFFFF"
          style={{ textDecoration: 'underline', letterSpacing: '0.5px' }}
        >
          {displayTitle}
        </text>

        {/* Y-axis gridlines and labels */}
        {ticks.map((t) => (
          <g key={t}>
            <line x1={left} x2={W - right} y1={y(t)} y2={y(t)} stroke="#404040" strokeWidth={0.6} />
            <text x={left - 6} y={y(t) + 3} fontSize={8} textAnchor="end" fill="#FFFFFF">
              {t.toFixed(2)}%
            </text>
          </g>
        ))}
        <line x1={left} x2={left} y1={top} y2={base} stroke="#555555" />
        <line x1={left} x2={W - right} y1={base} y2={base} stroke="#555555" />

        {/* Condition bars */}
        {bars.map((b, i) => {
          const cx = left + slot * i + slot / 2;
          const lines = [...wrap(b.name), `(${b.qty})`];
          const pctText = b.pct >= 99.995 ? '100%' : `${b.pct.toFixed(2)}%`;
          return (
            <g key={i}>
              <rect
                x={cx - barW / 2}
                y={y(b.pct)}
                width={barW}
                height={base - y(b.pct)}
                fill={b.colour}
                stroke="#1A1A1A"
                strokeWidth={0.5}
              />
              <text
                x={cx}
                y={y(b.pct) - 4}
                fontSize={n <= 10 ? 9 : 8}
                fontWeight="bold"
                textAnchor="middle"
                fill="#FFFFFF"
              >
                {pctText}
              </text>
              {lines.map((l, j) => (
                <text
                  key={j}
                  x={cx}
                  y={base + 14 + j * 10}
                  fontSize={labelSize}
                  textAnchor="middle"
                  fill="#FFFFFF"
                >
                  {l}
                </text>
              ))}
            </g>
          );
        })}
      </svg>
    </div>
  );
};

export default FindingsChart;

/**
 * The graph under a tally table, as the client draws it — the same rules as
 * backend/app/render/findings.py, so the preview shows what Word prints:
 * a column per condition found and a Total column at 100%, coloured by what
 * each is (sound green, soft yellow, rotten red, total blue), the percentage
 * on each and "SURVEY FINDINGS IN GRAPH" (or, in kg, "LOSS CALCULATION IN
 * GRAPH") underneath.
 */

export const GREEN = '#00B050';
export const YELLOW = '#FFFF00';
export const RED = '#FF0000';
export const BLUE = '#0070C0';
const OTHERS = ['#C00000', '#ED7D31', '#FFC000', '#7030A0', '#A5A5A5', '#BF8F00', '#843C0C'];

export function barColour(label: string, i: number): string {
  const low = label.toLowerCase();
  if (low.includes('sound') || low.includes('good')) return GREEN;
  if (low.includes('soft')) return YELLOW;
  if (['rot', 'decay', 'mould', 'mold', 'fung', 'wet'].some((w) => low.includes(w))) return RED;
  return OTHERS[i % OTHERS.length];
}

export function chartTitle(block: any): string {
  const t = String(block?.chart_title || '').split(/\s+/).filter(Boolean).join(' ');
  if (t) return t;
  return String(block?.unit || 'pcs').toLowerCase() === 'kg' ? 'LOSS CALCULATION IN GRAPH' : 'SURVEY FINDINGS IN GRAPH';
}

export function quantity(value: any, unit: string): string {
  const n = parseFloat(String(value ?? 0)) || 0;
  if (String(unit).toLowerCase() === 'kg') {
    const [i, d] = n.toFixed(3).split('.');
    return `${Number(i).toLocaleString('en-US')}.${d} Kg`;
  }
  return `${Math.round(n).toLocaleString('en-US')} Pcs`;
}

const cleanLabel = (label: string) => String(label).replace(/\s*\((?:pcs|kg|nos?)\.?\)\s*$/i, '').trim();

export interface Bar {
  name: string;
  qty: string;
  pct: number;
  colour: string;
}

/** Bars for the columns shown in the table, conditions first, then Total. */
export function chartBars(block: any, computed: any, shownKeys: string[]): Bar[] {
  const unit = block?.unit || 'pcs';
  const totals = computed?.column_totals || {};
  const pcts = computed?.column_percentages || {};
  const cats: any[] = (block?.categories || []).filter((c: any) => shownKeys.includes(c.key));
  const bars: Bar[] = [];
  let i = 0;
  cats.forEach((c) => {
    const total = parseFloat(String(totals[c.key] ?? 0)) || 0;
    if (total <= 0) return;
    const name = cleanLabel(c.label || c.key);
    bars.push({ name, qty: quantity(total, unit), pct: parseFloat(String(pcts[c.key] ?? 0)) || 0, colour: barColour(name, i) });
    i += 1;
  });
  if (bars.length && block?.chart_total_bar !== false && parseFloat(String(computed?.grand_total || 0)) > 0) {
    bars.push({ name: 'Total', qty: quantity(computed.grand_total, unit), pct: 100, colour: BLUE });
  }
  return bars;
}

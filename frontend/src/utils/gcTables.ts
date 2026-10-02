/**
 * General cargo tables, worked out as backend/app/compute/gc_tables.py does
 * (same rows, same wording, same number format), so the form, the A4
 * preview and the Word file show the same figures.
 */
import { DAMAGE_TABLE_COLUMNS, findingsRows } from './generalCargo';

export interface GridTable {
  title?: string;
  columns: string[];
  rows: string[][];
  total?: boolean;
}

const clean = (v: any) => String(v ?? '').split(/\s+/).filter(Boolean).join(' ');

export function num(v: any): number | null {
  const s = String(v ?? '').replace(/[,\s]/g, '');
  if (!s || !/^[+-]?(\d+\.?\d*|\.\d+)$/.test(s)) return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

export function fmt(n: number): string {
  const r = Math.round(n * 1000) / 1000;
  const s = r.toLocaleString('en-US', { maximumFractionDigits: 3 });
  return s === '-0' ? '0' : s;
}

export const signed = (n: number) => (n > 0 ? '+' : '') + fmt(n);

// ---------------------------------------------------------------------------
// Weighbridge
// ---------------------------------------------------------------------------

export const WEIGHT_COLUMNS = ['Particulars', 'Weight (kg)'];

export interface Weighbridge {
  rows: string[][];
  found: number | null;
  declared: number | null;
  diff: number | null;
  basis: string;
}

export function weighbridge(unit: any): Weighbridge | null {
  const w = unit?.weights || {};
  if (w.included === false) return null;
  const [gross, tareTruck, tareCont, declared] = ['gross', 'tare_truck', 'tare_container', 'declared'].map((k) => num(w[k]));
  if (gross === null && declared === null) return null;
  const basis = clean(w.basis) || 'B/L';
  const rows: string[][] = [];
  if (clean(w.weighbridge)) rows.push(['Weighbridge', clean(w.weighbridge)]);
  const slip = [clean(w.slip_no), clean(w.date)].filter(Boolean).join(' dated ');
  if (slip) rows.push(['Weight Slip No. and date', slip]);
  let found: number | null = null;
  const anyTare = tareTruck !== null || tareCont !== null;
  if (gross !== null) {
    const what = tareTruck !== null ? 'container + cargo + trailer' : tareCont !== null ? 'container + cargo' : 'cargo';
    rows.push([`Gross weight found of ${what}`, fmt(gross)]);
    if (tareTruck !== null) rows.push(['Less: Tare weight of trailer', fmt(tareTruck)]);
    if (tareCont !== null) rows.push(['Less: Marked tare weight of container', fmt(tareCont)]);
    found = gross - (tareTruck || 0) - (tareCont || 0);
    if (anyTare) rows.push(['Found gross weight of cargo', fmt(found)]);
  }
  if (declared !== null) rows.push([`Less: Gross weight of cargo as per ${basis === 'B/L' ? 'Bill of Lading' : basis}`, fmt(declared)]);
  const diff = found !== null && declared !== null ? found - declared : null;
  if (diff !== null) {
    const label = diff < 0 ? 'Difference (shortage)' : diff > 0 ? 'Difference (excess)' : 'Difference';
    rows.push([label, fmt(Math.abs(diff))]);
  }
  return { rows, found, declared, diff, basis };
}

// ---------------------------------------------------------------------------
// Tally
// ---------------------------------------------------------------------------

export function tally(unit: any): GridTable | null {
  const t = unit?.tally || {};
  if (t.included === false) return null;
  const basis = clean(t.basis) || 'Packing List';
  const columns = ['Description', `As per ${basis}`, 'Found sound', 'Found damaged', 'Shortage (-) / excess (+)'];
  const rows: string[][] = [];
  const totals = [0, 0, 0, 0];
  const counted = [false, false, false, false];
  for (const r of t.rows || []) {
    const item = clean(r.item);
    const vals = [num(r.document), num(r.sound), num(r.damaged)];
    if (!item && vals.every((v) => v === null)) continue;
    const [doc, sound, damaged] = vals;
    const diff = doc !== null && (sound !== null || damaged !== null) ? (sound || 0) + (damaged || 0) - doc : null;
    rows.push([item, ...vals.map((v) => (v !== null ? fmt(v) : '')), diff !== null ? signed(diff) : '']);
    [...vals, diff].forEach((v, i) => {
      if (v !== null) {
        totals[i] += v;
        counted[i] = true;
      }
    });
  }
  if (!rows.length) return null;
  if (rows.length > 1) rows.push(['Total', ...totals.map((v, i) => (counted[i] ? (i === 3 ? signed(v) : fmt(v)) : ''))]);
  return { columns, rows, total: rows.length > 1 };
}

// ---------------------------------------------------------------------------
// WEIGHT FINAL SUMMARY
// ---------------------------------------------------------------------------

export function weightSummary(blocks: any[]): GridTable | null {
  const units = (blocks || []).filter((b) => b.type === 'survey_unit' && b.included !== false);
  const items: [string, number, number][] = [];
  let basis = 'B/L';
  units.forEach((u, i) => {
    const w = weighbridge(u);
    if (!w || w.found === null || w.declared === null) return;
    basis = w.basis;
    items.push([clean(u.container) || `Survey ${i + 1}`, w.declared, w.found]);
  });
  if (items.length < 2) return null;
  // In the client's order: the weight ascertained, the weight as per the document, the difference.
  const rows = items.map(([label, dec, found]) => [label, fmt(found), fmt(dec), signed(found - dec)]);
  const td = items.reduce((a, x) => a + x[1], 0);
  const tf = items.reduce((a, x) => a + x[2], 0);
  rows.push(['Total', fmt(tf), fmt(td), signed(tf - td)]);
  return {
    title: 'WEIGHT FINAL SUMMARY',
    columns: ['Container No.', 'Ascertained weight (kg)', `Weight as per ${basis} (kg)`, 'Shortage (-) / excess (+) (kg)'],
    rows,
    total: true,
  };
}

// ---------------------------------------------------------------------------
// Report tables: containers & seals, weather, summary of reserve
// ---------------------------------------------------------------------------

export const REPORT_TABLE_FIELDS: Record<string, { key: string; label: string }[]> = {
  seals: [
    { key: 'container', label: 'Container No.' },
    { key: 'size', label: 'Size / Type' },
    { key: 'seal_doc', label: 'Seal No. as per B/L' },
    { key: 'seal_found', label: 'Seal No. found' },
  ],
  weather: [
    { key: 'place', label: 'Place' },
    { key: 'date', label: 'Date' },
    { key: 'rainfall', label: 'Rainfall' },
    { key: 'temperature', label: 'Max / Min temperature' },
  ],
  reserve: [
    { key: 'description', label: 'Description' },
    { key: 'quantity', label: 'Quantity' },
    { key: 'value', label: 'Invoice value' },
  ],
};

export const REPORT_TABLE_NAMES: Record<string, string> = {
  seals: 'Containers & seals',
  weather: 'Weather',
  reserve: 'Summary of reserve',
};

const normSeal = (s: string) => s.toUpperCase().replace(/[^A-Z0-9]/g, '');

/** "Yes" when the seal found is the one on the B/L (spaces and case aside), "No" when not, "" until both are in. */
export const sealTallies = (doc: any, found: any): string => {
  const [a, b] = [clean(doc), clean(found)];
  return a && b ? (normSeal(a) === normSeal(b) ? 'Yes' : 'No') : '';
};

export function reportTable(block: any): GridTable | null {
  const kind = block?.kind;
  const input: any[] = block?.rows || [];
  let title = '';
  let columns: string[];
  let rows: string[][] = [];
  if (kind === 'seals') {
    columns = ['Container No.', 'Size / Type', 'Seal No. as per B/L', 'Seal No. found', 'Tallies'];
    for (const r of input) {
      const cells = ['container', 'size', 'seal_doc', 'seal_found'].map((k) => clean(r[k]));
      if (!cells.some(Boolean)) continue;
      rows.push([...cells, sealTallies(cells[2], cells[3])]);
    }
  } else if (kind === 'weather') {
    columns = ['Place', 'Date', 'Rainfall', 'Max / Min temperature'];
    rows = input.map((r) => ['place', 'date', 'rainfall', 'temperature'].map((k) => clean(r[k]))).filter((c) => c.some(Boolean));
  } else if (kind === 'reserve') {
    title = 'SUMMARY OF RESERVE';
    const cur = clean(block.currency);
    columns = ['Description', 'Quantity', cur ? `Invoice value (${cur})` : 'Invoice value'];
    let total = 0;
    let any = false;
    for (const r of input) {
      const desc = clean(r.description);
      const qty = clean(r.quantity);
      const value = num(r.value);
      if (!desc && !qty && value === null) continue;
      rows.push([desc, qty, value !== null ? fmt(value) : clean(r.value)]);
      if (value !== null) {
        total += value;
        any = true;
      }
    }
    if (rows.length && any) rows.push(['Total', '', fmt(total)]);
  } else {
    return null;
  }
  if (!rows.length) return null;
  return { title, columns, rows, total: kind === 'reserve' && rows[rows.length - 1][0] === 'Total' };
}

// ---------------------------------------------------------------------------
// Where a survey paragraph's tables go
// ---------------------------------------------------------------------------

export const UNIT_TABLE_MARKS: Record<string, string> = {
  '(damage table)': 'damage',
  '(tally table)': 'tally',
  '(weight table)': 'weights',
};
const UNIT_TABLE_ORDER = ['damage', 'tally', 'weights'];

export type Segment = { kind: 'text'; value: string } | { kind: 'table'; value: string };

export function unitSegments(text: string): Segment[] {
  const out: Segment[] = [];
  let buf: string[] = [];
  const placed = new Set<string>();
  const trimNl = (s: string) => s.replace(/^\n+|\n+$/g, '');
  for (const line of String(text || '').split('\n')) {
    const key = UNIT_TABLE_MARKS[line.trim().toLowerCase()];
    if (key && !placed.has(key)) {
      out.push({ kind: 'text', value: trimNl(buf.join('\n')) });
      out.push({ kind: 'table', value: key });
      placed.add(key);
      buf = [];
    } else {
      buf.push(line);
    }
  }
  out.push({ kind: 'text', value: trimNl(buf.join('\n')) });
  for (const k of UNIT_TABLE_ORDER) if (!placed.has(k)) out.push({ kind: 'table', value: k });
  return out;
}

export function unitTable(unit: any, key: string): GridTable | null {
  if (key === 'damage') {
    const rows = findingsRows(unit);
    return rows.length ? { columns: DAMAGE_TABLE_COLUMNS, rows } : null;
  }
  if (key === 'tally') return tally(unit);
  if (key === 'weights') {
    const w = weighbridge(unit);
    return w && w.rows.length ? { columns: WEIGHT_COLUMNS, rows: w.rows } : null;
  }
  return null;
}

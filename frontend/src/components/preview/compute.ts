/**
 * Pure Client-Side Zero-Drift Arithmetic Engine.
 * Matches backend app.compute.arithmetic and photo_ranges bit-for-bit.
 * Uses Hare-Niemeyer Largest Remainder balancing to guarantee defect column/row
 * percentages sum exactly to 100.00%.
 */

/**
 * Hare-Niemeyer Largest Remainder Method
 * Distributes rounding error so percentages sum exactly to target (100.00%).
 */
export function hareNiemeyer(exactPcts: number[], target: number = 100.0): number[] {
  if (!exactPcts || exactPcts.length === 0) return [];

  // Floor to 2 decimal places
  const floors = exactPcts.map((p) => Math.floor(Math.round(p * 10000) / 100) / 100);
  const totalFloor = Math.round(floors.reduce((a, b) => a + b, 0) * 100) / 100;
  const deficit = Math.round((target - totalFloor) * 100);

  if (deficit <= 0) {
    return floors;
  }

  // Calculate remainders and sort descending by remainder, then ascending by index
  const remainders = exactPcts.map((p, i) => ({
    rem: Math.round((p - floors[i]) * 10000) / 10000,
    idx: i,
  }));
  remainders.sort((a, b) => b.rem - a.rem || a.idx - b.idx);

  for (let j = 0; j < deficit && j < floors.length; j++) {
    const targetIdx = remainders[j].idx;
    floors[targetIdx] = Math.round((floors[targetIdx] + 0.01) * 100) / 100;
  }

  return floors;
}

const COUNT_UNITS = ['pcs', 'pc', 'pieces', 'nos', 'no', 'boxes', 'cartons', 'ctns'];

export function computeTable(block: any): {
  row_totals: string[];
  row_percentages: string[][];
  column_totals: Record<string, string>;
  grand_total: string;
  column_percentages: Record<string, string>;
} {
  const categories: string[] = (block.categories || []).map((c: any) => c.key);
  const rows: any[] = block.rows || [];
  const unit: string = (block.unit || 'pcs').toLowerCase();
  const isKg = unit === 'kg';
  // Counted pieces total as whole numbers, as the backend and the client's
  // reports print them; a fraction somewhere keeps two places.
  const whole =
    COUNT_UNITS.includes(unit) &&
    rows.every((r) =>
      Object.values(r?.values || {}).every((v) => {
        const n = parseFloat(String(v ?? '').trim() || '0');
        return !Number.isFinite(n) || Number.isInteger(n);
      }),
    );
  const places = isKg ? 3 : whole ? 0 : 2;

  const colTotalsNum: Record<string, number> = {};
  categories.forEach((cat) => (colTotalsNum[cat] = 0));
  const rowTotalsFormatted: string[] = [];
  const rowPctsFormatted: string[][] = [];

  rows.forEach((row) => {
    let rSum = 0;
    const catVals: number[] = [];
    categories.forEach((cat) => {
      const v = parseFloat(String(row.values?.[cat] || 0)) || 0;
      catVals.push(v);
      rSum += v;
      colTotalsNum[cat] = (colTotalsNum[cat] || 0) + v;
    });

    const roundedSum = isKg
      ? Math.round(rSum * 1000) / 1000
      : Math.round(rSum * 100) / 100;
    rowTotalsFormatted.push(roundedSum.toFixed(places));

    if (roundedSum > 0) {
      const exactPcts = catVals.map((v) => (v / roundedSum) * 100);
      const balanced = hareNiemeyer(exactPcts);
      rowPctsFormatted.push(balanced.map((b) => b.toFixed(2)));
    } else {
      rowPctsFormatted.push(categories.map(() => '0.00'));
    }
  });

  const colTotalsFormatted: Record<string, string> = {};
  categories.forEach((cat) => {
    const val = isKg
      ? Math.round(colTotalsNum[cat] * 1000) / 1000
      : Math.round(colTotalsNum[cat] * 100) / 100;
    colTotalsFormatted[cat] = val.toFixed(places);
  });

  const rawGrand = Object.keys(colTotalsFormatted).reduce(
    (acc, k) => acc + parseFloat(colTotalsFormatted[k]),
    0
  );
  const grandTotalNum = isKg
    ? Math.round(rawGrand * 1000) / 1000
    : Math.round(rawGrand * 100) / 100;
  const grandTotalFormatted = grandTotalNum.toFixed(places);

  const colPctsFormatted: Record<string, string> = {};
  if (grandTotalNum > 0) {
    const exactColPcts = categories.map(
      (cat) => (parseFloat(colTotalsFormatted[cat]) / grandTotalNum) * 100
    );
    const balancedColPcts = hareNiemeyer(exactColPcts);
    categories.forEach((cat, idx) => {
      colPctsFormatted[cat] = balancedColPcts[idx].toFixed(2);
    });
  } else {
    categories.forEach((cat) => {
      colPctsFormatted[cat] = '0.00';
    });
  }

  return {
    row_totals: rowTotalsFormatted,
    row_percentages: rowPctsFormatted,
    column_totals: colTotalsFormatted,
    grand_total: grandTotalFormatted,
    column_percentages: colPctsFormatted,
  };
}

export interface SummaryGroup {
  key: string;
  boxes: number;
  column_totals: Record<string, string>;
  grand_total: string;
  column_percentages: Record<string, string>;
}

/**
 * The FINAL SUMMARY: rows grouped by container (or by count), each group's
 * totals and percentages. Same as compute_table_summary in the backend.
 */
export function computeTableSummary(block: any): { by: string; groups: SummaryGroup[]; boxes: number } | null {
  const opts = block?.summary || {};
  if (!opts.show) return null;
  const by = opts.by === 'container' ? 'container' : 'group';
  const order: string[] = [];
  const rowsBy: Record<string, any[]> = {};
  (block.rows || []).forEach((r: any) => {
    const k = String(r?.[by] ?? '').trim();
    if (!(k in rowsBy)) {
      order.push(k);
      rowsBy[k] = [];
    }
    rowsBy[k].push(r);
  });
  const boxes = (rows: any[]) =>
    rows.reduce((n, r) => n + (parseInt(String(r?.boxes_opened ?? 1), 10) || 1), 0);
  const groups = order.map((k) => {
    const c = computeTable({ ...block, rows: rowsBy[k] });
    return {
      key: k,
      boxes: boxes(rowsBy[k]),
      column_totals: c.column_totals,
      grand_total: c.grand_total,
      column_percentages: c.column_percentages,
    };
  });
  return { by, groups, boxes: groups.reduce((n, g) => n + g.boxes, 0) };
}

export function computePhotoRanges(groups: any[], startNumber: number = 1) {
  let current = startNumber;
  const groupResults: Record<string, any> = {};

  (groups || []).forEach((g) => {
    const gid = g.id || '';
    const assetIds = g.asset_ids || [];
    const count = assetIds.length;
    if (count === 0) {
      groupResults[gid] = {
        start: current,
        end: current,
        count: 0,
        numbers: [],
        label: '(No photos)',
      };
      return;
    }
    const startNo = current;
    const endNo = current + count - 1;
    const numbers: number[] = [];
    for (let i = startNo; i <= endNo; i++) numbers.push(i);
    current += count;

    let label = '';
    if (count === 1) label = `(Photo No. ${startNo})`;
    else if (count === 2) label = `(Photo Nos. ${startNo} & ${endNo})`;
    else label = `(Photo Nos. ${startNo} to ${endNo})`;

    groupResults[gid] = { start: startNo, end: endNo, count, numbers, label };
  });

  return {
    groups: groupResults,
    total_photos: current - startNumber,
    next_number: current,
  };
}

export function computeBlockState(blockState: any): any {
  if (!blockState) return blockState;
  const state = JSON.parse(JSON.stringify(blockState));
  const blocks = state.blocks || [];
  let photoCounter = 1;

  blocks.forEach((block: any) => {
    if (block.type === 'table') {
      block._computed = computeTable(block);
      const summary = computeTableSummary(block);
      if (summary) block._computed.summary = summary;
    } else if (block.type === 'photo_plate') {
      const res = computePhotoRanges(block.groups, photoCounter);
      block._computed = res;
      photoCounter += res.total_photos;
    } else {
      block._computed = { validated: true };
    }
  });

  return state;
}

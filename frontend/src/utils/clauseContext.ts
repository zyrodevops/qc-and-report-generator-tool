import type { ClauseContext } from '../api/client';

/** A value in the report that is still a placeholder is not a value. */
const real = (v: unknown): string => {
  const s = Array.isArray(v) ? String(v[0] ?? '') : v == null ? '' : String(v);
  const t = s.trim();
  return !t || t.startsWith('[') ? '' : t;
};

/**
 * What the pickers may fill in, taken from the report as it stands on screen
 * (saved or not). Anything missing stays a blank in the clause.
 */
export function clauseContextFrom(blockState: any): ClauseContext {
  const blocks: any[] = blockState?.blocks || [];
  const values: Record<string, string> = {};

  const particulars = blocks.find((b) => b.type === 'particulars');
  const container = (particulars?.rows || []).find((r: any) => /container/i.test(r.label || ''));
  // "TGHU1234567 (40' HC Reefer)" -> the number only.
  const containerNo = real(container?.value).match(/[A-Z]{4}\s?\d{6,7}/)?.[0];
  if (containerNo) values.container_no = containerNo.replace(/\s/g, '');

  const measurements = blocks.find((b) => b.type === 'measurements');
  for (const row of measurements?.rows || []) {
    const subject = String(row.subject || '').toLowerCase();
    const key = subject.includes('pulp') ? 'pulp' : subject.includes('brix') ? 'brix' : subject.includes('pressure') ? 'pressure' : null;
    if (!key) continue;
    if (real(row.min)) values[`${key}_min`] = real(row.min);
    if (real(row.max)) values[`${key}_max`] = real(row.max);
  }

  // The carrying temperature from the B/L / air waybill, once the documents are applied.
  const requested = blockState?.metadata?.shipment?.requested_temperature_c;
  if (Array.isArray(requested) ? requested.length : requested !== undefined && requested !== null && requested !== '') {
    (values as any).requested_temp = requested;
  }

  // Defects actually counted: columns with a figure above zero in any row.
  const defects: string[] = [];
  for (const table of blocks.filter((b) => b.type === 'table')) {
    for (const cat of table.categories || []) {
      if (/^sound$/i.test(cat.label || cat.key)) continue;
      const counted = (table.rows || []).some((r: any) => Number(r.values?.[cat.key]) > 0);
      if (counted) defects.push(String(cat.label || cat.key));
    }
  }

  return {
    commodity: blockState?.metadata?.commodity || undefined,
    mode: blockState?.transport?.mode || undefined,
    values,
    defects,
  };
}

export const BLANK_PATTERN = /\[[^\]\n]{1,40}\]/g;

/**
 * Blanks still waiting to be filled in the sections that will print: the
 * clause blanks ([DATE], [NAME] …) and the placeholders a new report starts
 * with ([Shipper Name, Country] …). Printed as they are, they would go out in
 * a signed report.
 */
export function findBlanks(blockState: any): { where: string; blanks: string[] }[] {
  const out: { where: string; blanks: string[] }[] = [];
  for (const b of blockState?.blocks || []) {
    if (b.included === false) continue;
    if (b.type === 'narrative') {
      const found = String(b.additional_text || '').match(BLANK_PATTERN);
      if (found?.length) out.push({ where: b.section || 'Text section', blanks: found });
    }
    if (b.type === 'particulars') {
      for (const row of b.rows || []) {
        const v = Array.isArray(row.value) ? row.value.join(' ') : String(row.value ?? '');
        const found = v.match(BLANK_PATTERN);
        if (found?.length) out.push({ where: row.label || 'Particulars', blanks: found });
      }
    }
  }
  return out;
}

/**
 * General cargo reports: the paragraph numbers and the OUR SURVEY headings,
 * worked out the same way as backend/app/compute/paragraphs.py so the form,
 * the preview and the Word file agree.
 */

export const isGeneralCargo = (state: any) => state?.metadata?.report_kind === 'general_cargo';

const clean = (v: any) => String(v ?? '').split(/\s+/).filter(Boolean).join(' ');

/** OUR SURVEY ON 22 JUNE 2026 AT THE CFS FOR CONTAINER NO. TSTU1234565: */
export function surveyTitle(block: any): string {
  const parts = [block?.joint ? 'OUR JOINT SURVEY' : 'OUR SURVEY'];
  if (clean(block?.survey_date)) parts.push(`ON ${clean(block.survey_date)}`);
  if (clean(block?.place)) parts.push(`AT ${clean(block.place)}`);
  if (clean(block?.container)) parts.push(`FOR CONTAINER NO. ${clean(block.container)}`);
  return `${parts.join(' ').toUpperCase()}:`;
}

/** Block id -> its numbered heading, for the included sections of a general cargo report. */
export function paragraphHeadings(state: any): Record<string, string> {
  const out: Record<string, string> = {};
  if (!isGeneralCargo(state)) return out;
  let top = 0;
  let sub = 0;
  for (const b of state?.blocks || []) {
    if (b?.included === false) continue;
    if (b.type === 'narrative' && b.numbered) {
      top += 1;
      sub = 0;
      out[b.id] = `PARAGRAPH ${top}: ${String(b.section || '').trim().replace(/:+$/, '')}:`;
    } else if (b.type === 'survey_unit') {
      sub += 1;
      out[b.id] = `PARAGRAPH ${Math.max(top, 1)}.${sub}: ${surveyTitle(b)}`;
    }
  }
  return out;
}

// ---------------------------------------------------------------------------
// The damage table of a survey paragraph (as backend/app/seeds/general_cargo.py)
// ---------------------------------------------------------------------------

export const DAMAGE_TABLE_MARK = '(damage table)';
export const DAMAGE_TABLE_COLUMNS = ['Sr. No.', 'Description', 'Quantity', 'Condition found', 'Photo Nos.'];

export interface Finding {
  item: string;
  total: string;
  affected: string;
  condition: string;
  photos: string;
}

/** The table's rows: [Sr. No., description, quantity, condition, photos]. */
export function findingsRows(block: any): string[][] {
  if (block?.findings_table === false) return [];
  const out: string[][] = [];
  for (const f of block?.findings || []) {
    const [item, total, affected, condition, photos] = [f.item, f.total, f.affected, f.condition, f.photos].map(clean);
    if (!item && !affected && !condition) continue;
    const qty = affected && total ? `${affected} of ${total}` : affected || total;
    out.push([String(out.length + 1), item, qty, condition, photos]);
  }
  return out;
}

/**
 * The text a findings list adds: the reports' line before the table, the
 * table's place, and for each kind of package with some left over "the
 * remaining [COUNT] [PACKAGES] were found in an apparently sound condition".
 * Only the archive's sentences (patterns) are used; without them, just the
 * table's place.
 */
export function writeFindings(findings: Finding[], patterns: Record<string, string>): string {
  const parts: string[] = [];
  if (patterns.lead) parts.push(patterns.lead);
  parts.push(DAMAGE_TABLE_MARK);
  const remaining = patterns.finding_remaining;
  if (remaining) {
    const byItem = new Map<string, { item: string; total: number; affected: number }>();
    for (const f of findings) {
      const item = clean(f.item);
      const total = Number(clean(f.total).replace(/,/g, ''));
      const affected = Number(clean(f.affected).replace(/,/g, '')) || 0;
      if (!item || !Number.isFinite(total) || total <= 0) continue;
      const key = item.toLowerCase();
      const cur = byItem.get(key) || { item, total, affected: 0 };
      cur.total = Math.max(cur.total, total);
      cur.affected += affected;
      byItem.set(key, cur);
    }
    for (const { item, total, affected } of byItem.values()) {
      const left = total - affected;
      if (left <= 0) continue;
      let s = remaining.split('[COUNT]').join(String(left)).split('[PACKAGES]').join(item);
      s = s.replace(/\s*\(Photo Nos?\.\s*\[PHOTO NOS\.\]\)/g, '').trim();
      parts.push(/[.:]$/.test(s) ? s : `${s}.`);
    }
  }
  return parts.join('\n\n');
}

/** The report tables and the section each follows (backend general_cargo.REPORT_TABLES). */
const REPORT_TABLES: [string, string, string][] = [
  ['b_seals', 'seals', 'b_circumstances'],
  ['b_weather', 'weather', 'b_cause'],
  ['b_reserve', 'reserve', 'b_next_step'],
];

/**
 * A general cargo report made before the report tables existed, with them
 * added (switched off) after their sections; null when nothing is missing.
 */
export function withReportTables(state: any): any | null {
  if (!isGeneralCargo(state)) return null;
  const blocks: any[] = [...(state?.blocks || [])];
  let changed = false;
  for (const [id, kind, after] of REPORT_TABLES) {
    if (blocks.some((b) => b.id === id)) continue;
    const at = blocks.findIndex((b) => b.id === after);
    if (at < 0) continue;
    blocks.splice(at + 1, 0, { id, type: 'gc_table', kind, rows: [], included: false });
    changed = true;
  }
  return changed ? { ...state, blocks } : null;
}

/** A new, empty OUR SURVEY paragraph with an id not yet used in the report. */
export function newSurveyUnit(blocks: any[], init: Partial<Record<string, string>> = {}): any {
  const taken = new Set((blocks || []).map((b: any) => b.id));
  let n = 1;
  while (taken.has(`b_survey_${n}`)) n += 1;
  return {
    id: `b_survey_${n}`,
    type: 'survey_unit',
    section: 'OUR_SURVEY',
    survey_date: init.survey_date || '',
    place: init.place || '',
    container: init.container || '',
    additional_text: '',
    attendance: [],
    included: true,
  };
}

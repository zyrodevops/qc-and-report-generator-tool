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

  const meta = blockState?.metadata || {};
  if (meta.report_kind === 'general_cargo') {
    Object.assign(values, generalCargoValues(blocks, meta.shipment));
    // Several containers: a sentence about "the container" names none of them
    // (a survey paragraph adds its own).
    if ((values as any).container_nos?.length > 1) delete values.container_no;
  }

  return {
    commodity: meta.commodity || undefined,
    mode: blockState?.transport?.mode || undefined,
    values,
    defects,
    cargo_type: meta.cargo_type || undefined,
    loss_types: meta.loss_types || [],
    state: meta.state || undefined,
  };
}

const CONTAINER_RE = /[A-Z]{4}\s?\d{7}/g;

/**
 * The facts a general cargo sentence names, from the cover and the first
 * survey paragraph: vessel, voyage, port and date of arrival, containers,
 * survey date and place. The names match gc_clause_library.SLOT_VALUES.
 */
export function generalCargoValues(blocks: any[], shipmentFacts?: any): Record<string, any> {
  const out: Record<string, any> = {};
  const rows: any[] = blocks.find((b) => b.type === 'particulars')?.rows || [];
  const field = (rx: RegExp) => real(rows.find((r) => rx.test(String(r.label || '')))?.value);

  const vessel = field(/vessel/i);
  if (vessel) {
    // "MSC ANNA / 123W", "MSC ANNA Voy. 123W"
    const [name, voyage] = vessel.split(/\s*(?:\/|\bVoy(?:age)?\.?\s*(?:No\.?)?)\s*/i);
    if (name) out.vessel = name.trim();
    if (voyage) out.voyage = voyage.trim();
  }
  const put = (key: string, v: string) => {
    if (v) out[key] = v;
  };
  put('port_of_discharge', field(/port of discharge/i));
  put('date_of_arrival', field(/date of arrival/i));
  put('airport_of_discharge', field(/airport of discharge/i));
  const flight = field(/flight/i);
  if (flight) put('flight_no', flight.split(/\s*(?:\/|\bdated\b|\bdt\.?)\s*/i)[0]);

  const containers = (field(/container/i).match(CONTAINER_RE) || []).map((c) => c.replace(/\s/g, ''));
  if (containers.length) out.container_nos = containers;
  const seals = field(/seal/i).split(/[,&/]|\band\b/).map((s) => s.trim()).filter(Boolean);
  if (seals.length === 1) out.seal_no = seals[0];

  // What the documents gave (EIR, tracking, lorry receipt), when applied.
  const ship = shipmentFacts;
  if (ship) {
    put('cfs', real(ship.cfs));
    put('delivery_date', real(ship.delivered_date));
    put('dispatch_date', real(ship.dispatch_date));
    put('delivery_place', real(ship.delivery_place));
    if (!out.date_of_arrival) put('date_of_arrival', real(ship.arrival_date));
  }

  // The first visit's date, place and people; the containers stay the cover's
  // (a paragraph's own container is for that paragraph's wording only).
  const survey = blocks.find((b) => b.type === 'survey_unit' && b.included !== false);
  if (survey) {
    const { container_no: _own, container_nos: _ownList, ...visit } = surveyUnitValues(survey);
    Object.assign(out, visit);
  }
  return out;
}

/** The named blanks of general cargo wording and the value each takes (gc_clause_library.SLOT_VALUES). */
const SLOT_KEYS: Record<string, string> = {
  '[VESSEL]': 'vessel',
  '[VOYAGE]': 'voyage',
  '[PORT OF DISCHARGE]': 'port_of_discharge',
  '[DATE OF ARRIVAL]': 'date_of_arrival',
  '[FLIGHT NO.]': 'flight_no',
  '[AIRPORT OF DISCHARGE]': 'airport_of_discharge',
  '[SURVEY DATE]': 'survey_date',
  '[PLACE OF SURVEY]': 'place_of_survey',
  '[SEAL NO.]': 'seal_no',
  '[REPRESENTATIVE]': 'representative',
  '[CFS]': 'cfs',
  '[DELIVERY DATE]': 'delivery_date',
  '[DISPATCH DATE]': 'dispatch_date',
  '[DELIVERY PLACE]': 'delivery_place',
};

function fillNamed(text: string, values: Record<string, any>): string {
  let out = text;
  for (const [slot, key] of Object.entries(SLOT_KEYS)) {
    if (values[key] && out.includes(slot)) out = out.split(slot).join(String(values[key]));
  }
  const containers: string[] = values.container_nos || [];
  if (values.container_no) out = out.split('[CONTAINER NO.]').join(values.container_no);
  if (containers.length) {
    const joined = containers.length === 1 ? containers[0] : `${containers.slice(0, -1).join(', ')} & ${containers[containers.length - 1]}`;
    out = out.split('[CONTAINER NOS.]').join(joined);
  }
  return out;
}

/**
 * General cargo wording names the report's own facts as named blanks
 * ([VESSEL], [SURVEY DATE] …). Wording is often added before the cover is
 * filled or the documents are read; when the value arrives, the blank in the
 * text already added is filled with it. Plain blanks ([NAME], [DATE]) are
 * never touched: nothing says which name or date they are.
 * Returns the new state, or null when nothing changed.
 */
export function fillNamedBlanks(blockState: any): any | null {
  if (blockState?.metadata?.report_kind !== 'general_cargo') return null;
  const blocks: any[] = blockState?.blocks || [];
  const base = generalCargoValues(blocks, blockState?.metadata?.shipment);
  if ((base.container_nos || []).length === 1) base.container_no = base.container_nos[0];
  else delete base.container_no;
  let changed = false;
  const next = blocks.map((b) => {
    if (b.type !== 'narrative' && b.type !== 'survey_unit') return b;
    const text = String(b.additional_text || '');
    if (!text.includes('[')) return b;
    let values = base;
    if (b.type === 'survey_unit') {
      values = { ...base };
      for (const k of ['survey_date', 'place_of_survey', 'representative', 'container_no']) delete values[k];
      Object.assign(values, surveyUnitValues(b));
    }
    const filled = fillNamed(text, values);
    if (filled === text) return b;
    changed = true;
    // The text each card added is kept, so "Remove" still finds it.
    const added = Object.fromEntries(Object.entries(b.wording_added || {}).map(([k, v]) => [k, fillNamed(String(v), values)]));
    return { ...b, additional_text: filled, wording_added: added };
  });
  return changed ? { ...blockState, blocks: next } : null;
}

/** What one survey paragraph adds: its date, place, container, whether joint, who attended. */
export function surveyUnitValues(unit: any): Record<string, any> {
  const out: Record<string, any> = {};
  if (real(unit.survey_date)) out.survey_date = real(unit.survey_date);
  if (real(unit.place)) out.place_of_survey = real(unit.place);
  out.joint = Boolean(unit.joint);
  const own = (String(unit.container || '').match(CONTAINER_RE) || [])[0];
  if (own) {
    out.container_no = own.replace(/\s/g, '');
    out.container_nos = [out.container_no];
  }
  const first = (unit.attendance || []).find((r: any) => real(r.name));
  if (first) out.representative = real(first.name);
  return out;
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
    if (b.type === 'narrative' || b.type === 'survey_unit') {
      const found = String(b.additional_text || '').match(BLANK_PATTERN);
      const where = b.type === 'survey_unit' ? `Our survey${b.container ? ` (${b.container})` : ''}` : b.section || 'Text section';
      if (found?.length) out.push({ where, blanks: found });
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

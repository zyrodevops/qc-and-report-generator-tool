import type { ClauseContext } from '../api/client';
import { normalizePort } from './portNormalizer';

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
  const rows: any[] = particulars?.rows || [];

  const containerRow = rows.find((r: any) => /container/i.test(r.label || ''));
  const containerVal = real(containerRow?.value);
  const containerMatches = containerVal.match(/[A-Z]{4}\s?\d{6,7}/g) || [];
  const firstContainer = containerMatches[0];
  if (firstContainer) {
    values.container_no = firstContainer.replace(/\s/g, '');
    (values as any).container_nos = containerMatches.map((c) => c.replace(/\s/g, ''));
  }

  const consigneeRow = rows.find((r: any) => /consignee/i.test(r.label || ''));
  const consigneeVal = real(consigneeRow?.value);
  if (consigneeVal) values.consignee = consigneeVal;

  const vesselRow = rows.find((r: any) => /vessel/i.test(r.label || ''));
  const vesselVal = real(vesselRow?.value);
  if (vesselVal) values.vessel = vesselVal;

  const voyageRow = rows.find((r: any) => /voyage\s+as\s+per\s+b\/l|port\s+of\s+discharge/i.test(r.label || ''));
  const voyageVal = real(voyageRow?.value);
  if (voyageVal) {
    let port = voyageVal;
    if (/\bto\b/i.test(voyageVal)) {
      const parts = voyageVal.split(/\bto\b/i);
      port = parts[parts.length - 1].trim();
    }
    if (port) {
      port = normalizePort(port);
      if (!/port/i.test(port)) {
        port = port.includes(',') ? port.replace(',', ' Port,') : `${port} Port`;
      }
      values.port_of_discharge = port;
    }
  }

  const arrivalRow = rows.find((r: any) => /date\s+of\s+arrival|arrival\s+date/i.test(r.label || ''));
  const arrivalVal = real(arrivalRow?.value);
  if (arrivalVal) {
    const dateMatch = arrivalVal.match(/\b\d{1,2}\s+[A-Za-z]+\s+\d{4}\b/);
    const dateStr = dateMatch ? dateMatch[0] : arrivalVal.split(/\s+at\s+|\s*\(/i)[0].trim();
    values.discharge_date = dateStr;
    values.date_of_arrival = dateStr;
  }

  const measurements = blocks.find((b) => b.type === 'measurements');
  for (const row of measurements?.rows || []) {
    const subject = String(row.subject || '').toLowerCase();
    const key = subject.includes('pulp')
      ? 'pulp'
      : subject.includes('brix')
      ? 'brix'
      : subject.includes('pressure')
      ? 'pressure'
      : subject.includes('berry') || subject.includes('size')
      ? 'berry'
      : null;
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
  const tables = blocks.filter((b) => b.type === 'table');
  let sampleBoxCount = 0;
  const countSet = new Set<string>();
function isSubtotalRow(row: any, precedingRows: any[]): boolean {
  if (precedingRows.length === 0) return false;
  const grp = String(row.group || '').toLowerCase();
  if (grp.includes('total') || grp.includes('subtotal') || grp.includes('sum')) {
    return true;
  }
  const getRowSum = (r: any): number => {
    if (r.stated_total && Number(r.stated_total) > 0) return Number(r.stated_total);
    let s = 0;
    for (const v of Object.values(r.values || {})) {
      const n = Number(v);
      if (!isNaN(n)) s += n;
    }
    return s;
  };
  const rowTotal = getRowSum(row);
  if (rowTotal > 0 && precedingRows.length >= 2) {
    let runningSum = 0;
    for (let i = precedingRows.length - 1; i >= 0; i--) {
      runningSum += getRowSum(precedingRows[i]);
      if (runningSum === rowTotal) return true;
      if (runningSum > rowTotal) break;
    }
  }
  const rowSound = Number(row.values?.sound ?? 0);
  if (rowSound > 0 && precedingRows.length >= 2) {
    let runningSound = 0;
    for (let i = precedingRows.length - 1; i >= 0; i--) {
      runningSound += Number(precedingRows[i].values?.sound ?? 0);
      if (runningSound === rowSound) return true;
      if (runningSound > rowSound) break;
    }
  }
  return false;
}

  for (const table of tables) {
    for (const cat of table.categories || []) {
      if (/^sound$/i.test(cat.label || cat.key)) continue;
      const counted = (table.rows || []).some((r: any) => Number(r.values?.[cat.key]) > 0);
      if (counted) defects.push(String(cat.label || cat.key));
    }
    const tableRows = table.rows || [];
    if (tableRows.length > 0) {
      const preceding: any[] = [];
      for (const r of tableRows) {
        const isSub = isSubtotalRow(r, preceding);
        preceding.push(r);
        if (isSub) continue;

        const cVal = r.group ?? r.count ?? r.size ?? r.counts ?? r.puc;
        if (cVal !== undefined && cVal !== null && String(cVal).trim() !== '') {
          const raw = String(cVal).trim();
          const n = parseInt(raw, 10);
          if (!isNaN(n) && n > 0) {
            // Standard fruit count numbers are <= 250 (e.g. 100, 120, 150, 165, 180, 198)
            // Numbers > 250 (e.g. 900, 825) are carton pieces subtotal rows, not count sizes.
            if (n <= 250) {
              countSet.add(String(n));
            }
          } else {
            countSet.add(raw);
          }
        }
      }
      let openedSum = 0;
      for (const r of tableRows) {
        if (r.boxes_opened && Number(r.boxes_opened) > 0) {
          openedSum += Number(r.boxes_opened);
        }
      }
      if (openedSum > 0) {
        sampleBoxCount += openedSum;
      } else {
        sampleBoxCount += tableRows.length;
      }
    }
  }

  // Fallback: if countSet is still empty, look at Particulars consignment tables
  if (countSet.size === 0) {
    const consignmentTables = rows.filter((r: any) =>
      r.type === 'table' ||
      Boolean(r.headers) ||
      ((r.label || '').toLowerCase().includes('consignment') && (Boolean(r.rows) || Boolean(r.items)))
    );
    for (const ct of consignmentTables) {
      const subItems: any[] = ct.rows || ct.items || [];
      for (const it of subItems) {
        const sVal = it.col2 ?? it.size ?? it.count ?? it.sizes ?? it.counts;
        if (sVal !== undefined && sVal !== null && String(sVal).trim() !== '') {
          const raw = String(sVal).trim();
          const n = parseInt(raw, 10);
          if (!isNaN(n) && n > 0) {
            if (n <= 250) {
              countSet.add(String(n));
            }
          } else {
            countSet.add(raw);
          }
        }
      }
    }
  }

  if (sampleBoxCount > 0) {
    values.sample_boxes = String(sampleBoxCount);
  }
  if (countSet.size > 0) {
    values.n_count = String(countSet.size);
    values.counts_count = `${countSet.size} counts`;
    values.sizes_count = `${countSet.size} sizes`;
  }

  // Consignee representative from attendance
  let consigneeRep = '';
  const narrativeBlocks = blocks.filter((b) => b.type === 'narrative' || b.type === 'attendance');
  for (const nb of narrativeBlocks) {
    const attList: any[] = nb.attendance || [];
    for (const att of attList) {
      const rep = (att.representing || '').toLowerCase();
      const isMCA = rep.includes('marine cargo agencies') || (att.name || '').includes('Baburao') || (att.name || '').includes('Bhosale');
      if (!isMCA && att.name?.trim()) {
        consigneeRep = att.name.trim();
        break;
      }
    }
    if (consigneeRep) break;
  }
  if (consigneeRep) values.representative_name = consigneeRep;

  // Total boxes from particulars or consignment table
  let foundTotalBoxes = '';

  // 1. Direct quantity row in particulars
  const qtyRow = rows.find((r: any) => /quantity|total\s+boxes|no\.\s+of\s+boxes|number\s+of\s+packages|cartons/i.test(r.label || ''));
  const qtyVal = real(qtyRow?.value);
  if (qtyVal) {
    const numMatch = qtyVal.match(/\b\d{1,3}(?:,\d{3})*\b/);
    if (numMatch) foundTotalBoxes = numMatch[0];
  }

  // 2. Consignment sub-tables in particulars
  if (!foundTotalBoxes) {
    const consignmentTables = rows.filter((r: any) =>
      r.type === 'table' ||
      Boolean(r.headers) ||
      ((r.label || '').toLowerCase().includes('consignment') && (Boolean(r.rows) || Boolean(r.items)))
    );
    for (const ct of consignmentTables) {
      const footerStr = String(ct.footer || (Array.isArray(ct.value) ? ct.value[0] : ct.value) || '');
      const footerMatch = footerStr.match(/total:?\s*([\d,]+)/i);
      if (footerMatch) {
        foundTotalBoxes = footerMatch[1];
        break;
      }
      const subItems: any[] = ct.rows || ct.items || [];
      let cTotal = 0;
      for (const it of subItems) {
        const bx = (it.col3 ?? it.boxes ?? it.cartons ?? it.total_boxes ?? '').toString().replace(/,/g, '').trim();
        const n = parseInt(bx, 10);
        if (!isNaN(n)) cTotal += n;
      }
      if (cTotal > 0) {
        foundTotalBoxes = cTotal.toLocaleString('en-US');
        break;
      }
    }
  }

  // 3. Shipment metadata
  if (!foundTotalBoxes) {
    const metaPkgs = (blockState?.metadata?.shipment?.total_packages ||
      blockState?.metadata?.shipment?.packages_count ||
      blockState?.metadata?.shipment?.total_cartons ||
      blockState?.metadata?.shipment?.total_boxes) as any;
    if (metaPkgs) {
      const match = String(metaPkgs).match(/\b\d{1,3}(?:,\d{3})*\b/);
      if (match) foundTotalBoxes = match[0];
    }
  }

  // 4. Nature of Packing in particulars
  if (!foundTotalBoxes) {
    const packingRow = rows.find((r: any) => /nature\s+of\s+packing|packing/i.test(r.label || ''));
    const packingVal = real(packingRow?.value);
    if (packingVal) {
      const pMatch = packingVal.match(/(\d{1,3}(?:,\d{3})*|\d+)\s*(?:boxes|cartons|trays|packages)\b/i);
      if (pMatch) foundTotalBoxes = pMatch[1];
    }
  }

  if (foundTotalBoxes) {
    values.total_boxes = foundTotalBoxes;
  }

  const meta = blockState?.metadata || {};
  let detectedCommodity = meta.commodity || undefined;
  if (!detectedCommodity) {
    const title = String(blockState?.report_title || '');
    const match = title.match(/\b(APPLE|PEAR|PLUM|GRAPES?|MANDARINS?|ORANGE|KIWI|MANGO|BANANA)\b/i);
    if (match) {
      detectedCommodity = match[1].toLowerCase().replace(/s$/, '');
    }
  }

  if (meta.report_kind === 'general_cargo') {
    Object.assign(values, generalCargoValues(blocks, meta.shipment));
    // Several containers: a sentence about "the container" names none of them
    // (a survey paragraph adds its own).
    if ((values as any).container_nos?.length > 1) delete values.container_no;
  }

  return {
    commodity: detectedCommodity,
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

/**
 * Builds standard Paragraph 2 Circumstances of Loss text based on Reports M-162, M-163 (Pear) & M-164 (Apple).
 * Auto-fills known variables from the top table (particulars), leaving missing ones as clean blanks.
 */
export function buildCircumstancesText(clauseContext: ClauseContext, fruitLabel: string = 'Apple'): string {
  const vals = clauseContext.values || {};
  const vessel = vals.vessel?.trim() || '[Vessel Name & Voyage No.]';
  const port = vals.port_of_discharge?.trim() || '[Port of Discharge]';
  const date = vals.discharge_date?.trim() || vals.date_of_arrival?.trim() || '[Discharge Date]';

  const containerList: string[] = (vals as any).container_nos || (vals.container_no ? [vals.container_no] : []);
  let containerText = "40' Reefer container No. [Container No.]";
  if (containerList.length === 1) {
    containerText = `40' Reefer container No. ${containerList[0]}`;
  } else if (containerList.length > 1) {
    containerText = `40' Reefer container Nos. ${containerList.join(', ')}`;
  }

  return (
    `We were apprised that subsequent to its discharge from the vessel ${vessel} ` +
    `at ${port}, on ${date}, the ${containerText}, conveying the subject cargo, ` +
    `was transferred to the designated Container Freight Station (CFS) for the purpose of customs formalities and ultimate delivery.\n\n` +
    `Following the culmination of customs procedures, the aforementioned container was loaded onto a trailer truck, dispatched, ` +
    `and transported via road. It was reported to have been delivered to the consignees' cold storage facility on [Delivery Date], ` +
    `ostensibly in an externally sound condition. We were further given to comprehend that during the destuffing and subsequent inspection, ` +
    `the consignees' Quality Control Team identified that the ${fruitLabel} fruits had sustained damage. ` +
    `Consequently, we were contacted and formally requested to undertake the survey.`
  );
}

export function buildAppleCircumstances(clauseContext: ClauseContext): string {
  return buildCircumstancesText(clauseContext, 'Apple');
}

export function buildPearCircumstances(clauseContext: ClauseContext): string {
  return buildCircumstancesText(clauseContext, 'Pear');
}

/**
 * Builds standard Paragraph 2 Circumstances of Loss text for Mandarin based on Reports M-165 & M-166.
 * Auto-fills known variables from the top table (particulars), leaving missing ones as clean blanks.
 */
export function buildMandarinCircumstances(clauseContext: ClauseContext): string {
  const vals = clauseContext.values || {};
  const vessel = vals.vessel?.trim() || '[Vessel Name & Voyage No.]';
  const port = vals.port_of_discharge?.trim() || '[Port of Discharge]';
  const date = vals.discharge_date?.trim() || vals.date_of_arrival?.trim() || '[Discharge Date]';

  const containerList: string[] = (vals as any).container_nos || (vals.container_no ? [vals.container_no] : []);
  let containerText = "the subject 1x40’ Reefer Container No. [Container No.]";
  if (containerList.length === 1) {
    containerText = `the subject 1x40’ Reefer Container No. ${containerList[0]}`;
  } else if (containerList.length > 1) {
    containerText = `the subject Reefer Container Nos. ${containerList.join(', ')}`;
  }

  return (
    `It was reported to us that after landing from the vessel ${vessel} ` +
    `at ${port} on ${date}, ${containerText} ` +
    `carrying the subject cargo was gated out and shifted to the nominated Container Freight Station (CFS) for customs formalities and delivery. ` +
    `On completion of custom formalities, the subject container was loaded onto the trailer truck, dispatched, road transported and was said to have been delivered at the consignees’ cold storage in an apparently sound condition.\n\n` +
    `We were further given to understand that during destuffing and checking, the consignees’ QC team found mandarin fruits in a damaged condition. ` +
    `Hence, we were contacted and requested to conduct the survey.`
  );
}

/**
 * Builds standard Paragraph 2 Circumstances of Loss text for Grapes based on Reports M-167 & M-168.
 * Auto-fills known variables from the top table (particulars), leaving missing ones as clean blanks.
 */
export function buildGrapesCircumstances(clauseContext: ClauseContext): string {
  const vals = clauseContext.values || {};
  const vessel = vals.vessel?.trim() || '[Vessel Name & Voyage No.]';
  const port = vals.port_of_discharge?.trim() || '[Port of Discharge]';
  const date = vals.discharge_date?.trim() || vals.date_of_arrival?.trim() || '[Discharge Date]';

  const containerList: string[] = (vals as any).container_nos || (vals.container_no ? [vals.container_no] : []);
  let containerText = "the subject 1x40’ Reefer Container No. [Container No.]";
  let dispatchText = "the subject container was dispatched, road transported, and was said to have been delivered at the consignees’ cold storage in an apparently sound condition on [Delivery Date]";
  if (containerList.length === 1) {
    containerText = `the subject 1x40’ Reefer Container No. ${containerList[0]}`;
  } else if (containerList.length > 1) {
    containerText = `the subject Reefer Container Nos. ${containerList.join(', ')}`;
    dispatchText = "the subject containers were dispatched, road transported, and were said to have been delivered at the consignees’ cold storage in an apparently sound condition on [Delivery Date]";
  }

  return (
    `It was reported to us that after discharge from the carrying vessel ${vessel} ` +
    `at ${port} on ${date}, ${containerText} ` +
    `carrying the subject cargo was drayed by truck and received at the inland depot / CFS for customs formalities and delivery. ` +
    `On completion of customs formalities, ${dispatchText}.\n\n` +
    `We were further given to understand that during destuffing and checking, the consignees’ QC team found fresh grape fruits in a damaged condition. ` +
    `Hence, we were contacted and requested to conduct the survey.`
  );
}

/**
 * Builds standard Paragraph 2 Circumstances of Loss text for Plum based on Report M-160.
 * Auto-fills known variables from the top table (particulars), leaving missing ones as clean blanks.
 */
export function buildPlumCircumstances(clauseContext: ClauseContext): string {
  const vals = clauseContext.values || {};
  const vessel = vals.vessel?.trim() || '[Vessel Name & Voyage No.]';
  const port = vals.port_of_discharge?.trim() || '[Port of Discharge]';
  const date = vals.discharge_date?.trim() || vals.date_of_arrival?.trim() || '[Discharge Date]';

  const containerList: string[] = (vals as any).container_nos || (vals.container_no ? [vals.container_no] : []);
  let containerText = "the 1x40’ High Cube refrigerated container (No. [Container No.])";
  let trailerText = "the container was loaded onto a road trailer, dispatched, and delivered at the Consignee’s nominated cold storage facility on [Delivery Date] in an externally sound condition";
  let openText = "during opening the container and initial inspection of the cargo from the door end";
  if (containerList.length === 1) {
    containerText = `the 1x40’ High Cube refrigerated container (No. ${containerList[0]})`;
  } else if (containerList.length > 1) {
    containerText = `the ${containerList.length}x40’ High Cube refrigerated containers (Nos. ${containerList.join(' & ')})`;
    trailerText = "the containers were loaded onto road trailers, dispatched, and delivered at the Consignee’s nominated cold storage facility on [Delivery Date] in an externally sound condition";
    openText = "during opening the containers and initial inspection of the cargo from the door end";
  }

  return (
    `It was reported that following discharge from the vessel ${vessel} ` +
    `at ${port}, on ${date}, ${containerText} ` +
    `carrying the subject cargo was shifted to the nominated Container Freight Station (CFS) for customs clearance and subsequent delivery. ` +
    `Upon completion of customs formalities, ${trailerText}.\n\n` +
    `We were further informed that ${openText}, the Consignee’s Quality Control (QC) In-Charge found the fresh plums in a severely deteriorated condition, ` +
    `exhibiting extensive rotting and fungal decay. Consequently, our attendance was requested to conduct a survey to ascertain the nature, extent, and cause of the reported damage.`
  );
}

export const MANDARIN_NOTE_TEXT =
  'Upon our arrival, we noted that the container was no longer available on site. ' +
  'The consignees advised us that the container was released to avoid detention charges.';

/**
 * Fills any known top-table values into existing placeholders in Paragraph 2.
 */
export function fillCircumstancesBlanks(text: string, clauseContext: ClauseContext): string {
  let updated = text;
  const vals = clauseContext.values || {};

  if (vals.vessel?.trim() && updated.includes('[Vessel Name & Voyage No.]')) {
    updated = updated.split('[Vessel Name & Voyage No.]').join(vals.vessel.trim());
  }

  if (vals.port_of_discharge?.trim() && updated.includes('[Port of Discharge]')) {
    updated = updated.split('[Port of Discharge]').join(vals.port_of_discharge.trim());
  }

  const date = vals.discharge_date?.trim() || vals.date_of_arrival?.trim();
  if (date && updated.includes('[Discharge Date]')) {
    updated = updated.split('[Discharge Date]').join(date);
  }

  const containerList: string[] = (vals as any).container_nos || (vals.container_no ? [vals.container_no] : []);
  if (containerList.length === 1) {
    if (updated.includes('[Container No.]')) {
      updated = updated.split('[Container No.]').join(containerList[0]);
    }
  } else if (containerList.length > 1) {
    // Apple / Pear
    if (updated.includes("40' Reefer container No. [Container No.]")) {
      updated = updated.split("40' Reefer container No. [Container No.]").join(`40' Reefer container Nos. ${containerList.join(', ')}`);
    }
    // Mandarin / Grapes
    if (updated.includes("the subject 1x40’ Reefer Container No. [Container No.]")) {
      updated = updated.split("the subject 1x40’ Reefer Container No. [Container No.]").join(`the subject Reefer Container Nos. ${containerList.join(', ')}`);
    } else if (updated.includes("the subject 1x40' Reefer Container No. [Container No.]")) {
      updated = updated.split("the subject 1x40' Reefer Container No. [Container No.]").join(`the subject Reefer Container Nos. ${containerList.join(', ')}`);
    }
    // Plum
    if (updated.includes("the 1x40’ High Cube refrigerated container (No. [Container No.])")) {
      updated = updated.split("the 1x40’ High Cube refrigerated container (No. [Container No.])").join(`the ${containerList.length}x40’ High Cube refrigerated containers (Nos. ${containerList.join(' & ')})`);
    } else if (updated.includes("the 1x40' High Cube refrigerated container (No. [Container No.])")) {
      updated = updated.split("the 1x40' High Cube refrigerated container (No. [Container No.])").join(`the ${containerList.length}x40' High Cube refrigerated containers (Nos. ${containerList.join(' & ')})`);
    }
    // Plum multi-container sentence adjustments
    if (updated.includes("the container was loaded onto a road trailer, dispatched, and delivered")) {
      updated = updated.split("the container was loaded onto a road trailer, dispatched, and delivered").join("the containers were loaded onto road trailers, dispatched, and delivered");
    }
    if (updated.includes("during opening the container and initial inspection")) {
      updated = updated.split("during opening the container and initial inspection").join("during opening the containers and initial inspection");
    }
    // Grapes multi-container sentence adjustment
    if (updated.includes("the subject container was dispatched, road transported")) {
      updated = updated.split("the subject container was dispatched, road transported").join("the subject containers were dispatched, road transported");
    }
    if (updated.includes('[Container No.]')) {
      updated = updated.split('[Container No.]').join(containerList.join(', '));
    }
  }

  return updated;
}

export const fillAppleCircumstancesBlanks = fillCircumstancesBlanks;

/**
 * Builds standard Paragraph 2.1 Our Survey text for Apple based on Reports M-161 & M-164.
 */
export function buildAppleOurSurvey(clauseContext: ClauseContext): string {
  const vals = clauseContext.values || {};
  const rep = vals.representative_name?.trim() || '[Representative Name]';
  const totalBoxes = vals.total_boxes?.trim() || '[Total Boxes]';
  const nCount = vals.n_count?.trim() || (vals.counts_count ? vals.counts_count.match(/\d+/)?.[0] : '') || '';
  const countsCount = nCount ? `${nCount} counts` : (vals.counts_count?.trim() || '[N] counts');
  const pulpMin = vals.pulp_min?.trim();
  const pulpMax = vals.pulp_max?.trim();
  const pulpRange = pulpMin && pulpMax ? `${pulpMin}°C to ${pulpMax}°C` : '[Pulp Temp Min °C] to [Pulp Temp Max °C]';

  const pressMin = vals.pressure_min?.trim();
  const pressMax = vals.pressure_max?.trim();
  const pressRange = pressMin && pressMax ? `Range of ${pressMin} LBS to ${pressMax} LBS.` : 'Range of [Fruit Pressure Min LBS] to [Fruit Pressure Max LBS].';

  const brixMin = vals.brix_min?.trim();
  const brixMax = vals.brix_max?.trim();
  const brixRange = brixMin && brixMax ? `${brixMin}% to ${brixMax}%` : '[Brix Min %] to [Brix Max %]';

  const sampleBoxes = vals.sample_boxes?.trim() || '[Sample Boxes]';

  return (
    `The consignee's end buyer representative, ${rep}, presented ${totalBoxes} boxes across ${countsCount} on various pallets for our survey. ` +
    `These were stored in cold storage room number [Room No.], where the ambient temperature was recorded as [Room Temp °C].\n\n` +
    `THE CONDITION FOUND OF APPLE FRUITS:\n\n` +
    `The pulp temperature of the Apple fruits was measured inside the cold room using a digital thermometer and registered in the range of ${pulpRange}.\n\n` +
    `From different locations within the cold room, ${sampleBoxes} boxes across ${countsCount} were randomly selected and opened for detailed examination. ` +
    `Upon unpacking and inspection, the Apple fruits inside the cartons exhibited a mixture of conditions, including sound, and various degrees of rotten.\n\n` +
    `The pressure of the randomly selected various Apple fruits across ${countsCount} were measured using a penetrometer, and the following average values were recorded for the sound apples:\n` +
    `• ${pressRange}\n\n` +
    `The Apple fruits were cut, and the following pulp conditions were observed:\n` +
    `• Sound apples: The pulp was consistently hard and white.\n` +
    `• Bruised apples: While the overall pulp remained firm, the bruised areas were noted to be soft and brown in colour.\n` +
    `• The sugar brix for the aforementioned counts was measured and found to be in the range of ${brixRange}.\n\n` +
    `During our inspection, ${sampleBoxes} boxes out of the ${totalBoxes} boxes (under ${countsCount}) were separated into the following categories. ` +
    `The details for each category are provided below:`
  );
}

/**
 * Builds standard Paragraph 2.1 Our Survey text for Pear based on Reports M-162 & M-163.
 */
export function buildPearOurSurvey(clauseContext: ClauseContext): string {
  const vals = clauseContext.values || {};
  const rep = vals.representative_name?.trim() || '[Representative Name]';
  const totalBoxes = vals.total_boxes?.trim() || '[Total Boxes]';
  const nCount = vals.n_count?.trim() || (vals.counts_count ? vals.counts_count.match(/\d+/)?.[0] : '') || '';
  const countsCount = nCount ? `${nCount} counts` : (vals.counts_count?.trim() || 'available [N] counts');
  const pulpMin = vals.pulp_min?.trim();
  const pulpMax = vals.pulp_max?.trim();
  const pulpRange = pulpMin && pulpMax ? `${pulpMin}°C to ${pulpMax}°C` : '[Pulp Temp Min °C] to [Pulp Temp Max °C]';

  const pressMin = vals.pressure_min?.trim();
  const pressMax = vals.pressure_max?.trim();
  const pressRange = pressMin && pressMax ? `Range of ${pressMin} LBS to ${pressMax} LBS.` : 'Range of [Fruit Pressure Min LBS] to [Fruit Pressure Max LBS].';

  const brixMin = vals.brix_min?.trim();
  const brixMax = vals.brix_max?.trim();
  const brixRange = brixMin && brixMax ? `${brixMin}% to ${brixMax}%` : '[Brix Min %] to [Brix Max %]';

  const sampleBoxes = vals.sample_boxes?.trim() || '[Sample Boxes]';

  return (
    `The consignee's representative, ${rep}, presented ${totalBoxes} boxes across ${countsCount} for our survey. ` +
    `These were stored in cold storage room number [Room No.], where the ambient temperature was recorded as [Room Temp °C].\n\n` +
    `THE CONDITION FOUND OF PEAR FRUITS:\n\n` +
    `The pulp temperature of the Pear fruits was measured inside the cold room using a digital thermometer and registered in the range of ${pulpRange}.\n\n` +
    `From different locations within the cold room, ${sampleBoxes} boxes across ${countsCount} were randomly selected and opened for detailed examination. ` +
    `Upon unpacking and inspection, the Pear fruits inside the cartons exhibited a mixture of conditions, including sound and in a rotten condition in various degrees.\n\n` +
    `The pressure of the Pear fruits under ${countsCount} was measured using a penetrometer, and the following average values were recorded for the sound Pears:\n` +
    `• ${pressRange}\n\n` +
    `The Pear fruits were cut, and the following pulp conditions were observed:\n` +
    `• Sound Pears: The pulp was consistently hard.\n` +
    `• The sugar brix for the above counts was measured and found to be in the range of ${brixRange}.\n\n` +
    `During our inspection, ${sampleBoxes} boxes out of the ${totalBoxes} boxes (under ${countsCount}) were separated into the following categories. ` +
    `The details for each category are provided below:`
  );
}

/**
 * Builds standard Paragraph 2.1 Our Survey text for Mandarin based on Reports M-165 & M-166.
 */
export function buildMandarinOurSurvey(clauseContext: ClauseContext): string {
  const vals = clauseContext.values || {};
  const rep = vals.representative_name?.trim() || '[Representative Name]';
  const totalBoxes = vals.total_boxes?.trim() || '[Total Cartons]';
  const nCount = vals.n_count?.trim() || (vals.sizes_count ? vals.sizes_count.match(/\d+/)?.[0] : '') || '';
  const sizesCount = nCount ? `${nCount} sizes` : (vals.sizes_count?.trim() || '[N] sizes');
  const pulpMin = vals.pulp_min?.trim();
  const pulpMax = vals.pulp_max?.trim();
  const pulpRange = pulpMin && pulpMax ? `${pulpMin}°C to ${pulpMax}°C` : '[Pulp Temp Min °C] to [Pulp Temp Max °C]';

  const brixMin = vals.brix_min?.trim();
  const brixMax = vals.brix_max?.trim();
  const brixRange = brixMin && brixMax ? `${brixMin}% to ${brixMax}%` : '[Brix Min %] to [Brix Max %]';

  const sampleBoxes = vals.sample_boxes?.trim() || '[Sample Boxes]';

  return (
    `The consignees’ representative ${rep}, produced before us the ${totalBoxes} cartons under ${sizesCount} for our survey, ` +
    `stored inside the cold storage no. [Room No.]. Cold room display temperature was found maintained at [Room Temp °C].\n\n` +
    `The pulp temperature of the fresh mandarin fruits was checked by means of a digital thermometer inside the cold room and was found in the range of ${pulpRange}.\n\n` +
    `Thereafter, a total of ${sampleBoxes} cartons was randomly selected from various pallets / different locations inside the cold room and were opened for our detailed survey, ` +
    `when we found the mandarin fruits inside the cartons with mixture of sound, soft/pressed, mechanical injury, rotten spot, and in a rotten condition in various degrees.\n\n` +
    `• Upon cutting the mandarin fruits, the pulp was found juicy.\n` +
    `• Brix was checked and was found in the range of ${brixRange}.\n\n` +
    `Based on our survey findings, upon segregation of mandarin fruits from the ${sampleBoxes} cardboard boxes, we can conclude that the mandarin fruits were found with the following defects:`
  );
}

/**
 * Builds standard Paragraph 2.1 Our Survey text for Grapes based on Reports M-167 & M-168.
 */
export function buildGrapesOurSurvey(clauseContext: ClauseContext): string {
  const vals = clauseContext.values || {};
  const rep = vals.representative_name?.trim() || '[Representative Name]';
  const totalBoxes = vals.total_boxes?.trim() || '[Total Boxes]';
  const pulpMin = vals.pulp_min?.trim();
  const pulpMax = vals.pulp_max?.trim();
  const pulpRange = pulpMin && pulpMax ? `${pulpMin}°C to ${pulpMax}°C` : '[Pulp Temp Min °C] to [Pulp Temp Max °C]';

  const brixMin = vals.brix_min?.trim();
  const brixMax = vals.brix_max?.trim();
  const brixRange = brixMin && brixMax ? `${brixMin}% to ${brixMax}%` : '[Brix Min %] to [Brix Max %]';

  const berryMin = vals.berry_min?.trim();
  const berryMax = vals.berry_max?.trim();
  const berryRange = berryMin && berryMax ? `${berryMin} mm to ${berryMax} mm` : '[Berry Size Min mm] to [Berry Size Max mm]';

  const sampleBoxes = vals.sample_boxes?.trim() || '[Sample Boxes]';

  return (
    `The consignee’s representative, ${rep}, presented for inspection the ${totalBoxes} boxes stored inside cold room No. [Room No.]. ` +
    `The cold room's temperature display indicated [Room Temp °C].\n\n` +
    `The pulp temperature of the grapes was checked using a digital probe thermometer inside the cold room within the boxes, ` +
    `whereby the temperature was recorded in the range of ${pulpRange}.\n\n` +
    `Thereafter, a total of ${sampleBoxes} boxes from the cold room were randomly selected from various stacks at different locations of the cold room ` +
    `and were opened for our survey when we found the grapes inside the boxes with a mixture of sound, soft, and in a rotten condition in varying degrees.\n\n` +
    `• Upon cutting the sound berries, the pulp was found hard and partially white.\n` +
    `• Upon cutting the soft berries, the pulp was found soft and dark in colour.\n` +
    `• The average sugar brix of the grapes was checked and found in the range of ${brixRange}.\n` +
    `• Grape’s berries size was checked using a vernier caliper and was found in the range of ${berryRange}.\n\n` +
    `During our inspection, ${sampleBoxes} boxes out of the ${totalBoxes} boxes were segregated into the following categories. ` +
    `The category wise details are given below:`
  );
}

/**
 * Builds standard Paragraph 2.1 Our Survey text for Plum based on Report M-160.
 */
export function buildPlumOurSurvey(clauseContext: ClauseContext): string {
  const vals = clauseContext.values || {};
  const rep = vals.representative_name?.trim() || '[Representative Name]';
  const containerNo = vals.container_no?.trim() || '[Container No.]';
  const totalBoxes = vals.total_boxes?.trim() || '[Total Cartons]';
  const pulpMin = vals.pulp_min?.trim();
  const pulpMax = vals.pulp_max?.trim();
  const pulpRange = pulpMin && pulpMax ? `${pulpMin}°C to ${pulpMax}°C` : '[Pulp Temp Min °C] to [Pulp Temp Max °C]';

  const sampleBoxes = vals.sample_boxes?.trim() || '[Sample Boxes]';

  return (
    `The Consignees’ representative ${rep} produced before us the subject 40’ Reefer Container No. ${containerNo} for our survey. ` +
    `Upon checking the same, the details noted are as follows:\n\n` +
    `• The refrigerated container ${containerNo}, laden with fresh plums, was inspected at the cold storage unloading ramp and was found ` +
    `structurally sound with standard wear and tear, fully plugged into the electrical main, and actively powered on.\n` +
    `• Reefer operational parameters registered a set point of [Set Temp °C], supply air temperature of [Supply Temp °C], and return air temperature of [Return Temp °C].\n` +
    `• Pulp temperatures drawn inside the container across different locations using a digital probe thermometer ranged from ${pulpRange}.\n` +
    `• Under continuous surveyor supervision, 100% destuffing of the consignment comprising ${totalBoxes} cartons was completed and transferred directly into the cold storage facility.\n` +
    `• A representative sample of ${sampleBoxes} cartons was drawn across the stow for detailed segregation and defect classification.\n\n` +
    `Pulp condition after cutting & the Taste:\n` +
    `• Cross-sectional cutting of representative fruit specimens revealed internal breakdown, water-soaking, and deep flesh browning.\n` +
    `• Organoleptic evaluation indicated severe textural degradation; the pulp was mushy, lacked characteristic varietal firmness, and had acquired an offensive, fermented taste.`
  );
}

/**
 * Fills any known measurements, attendance, or particulars values into existing placeholders in Paragraph 2.1.
 */
export function fillOurSurveyBlanks(text: string, clauseContext: ClauseContext): string {
  let updated = text;
  const vals = clauseContext.values || {};

  const pulpMin = vals.pulp_min?.trim();
  const pulpMax = vals.pulp_max?.trim();
  if (pulpMin && pulpMax && updated.includes('[Pulp Temp Min °C] to [Pulp Temp Max °C]')) {
    updated = updated.split('[Pulp Temp Min °C] to [Pulp Temp Max °C]').join(`${pulpMin}°C to ${pulpMax}°C`);
  }

  const brixMin = vals.brix_min?.trim();
  const brixMax = vals.brix_max?.trim();
  if (brixMin && brixMax && updated.includes('[Brix Min %] to [Brix Max %]')) {
    updated = updated.split('[Brix Min %] to [Brix Max %]').join(`${brixMin}% to ${brixMax}%`);
  }

  const pressMin = vals.pressure_min?.trim();
  const pressMax = vals.pressure_max?.trim();
  if (pressMin && pressMax && updated.includes('[Fruit Pressure Min LBS] to [Fruit Pressure Max LBS]')) {
    updated = updated.split('[Fruit Pressure Min LBS] to [Fruit Pressure Max LBS]').join(`${pressMin} LBS to ${pressMax} LBS`);
  }

  const berryMin = vals.berry_min?.trim();
  const berryMax = vals.berry_max?.trim();
  if (berryMin && berryMax && updated.includes('[Berry Size Min mm] to [Berry Size Max mm]')) {
    updated = updated.split('[Berry Size Min mm] to [Berry Size Max mm]').join(`${berryMin} mm to ${berryMax} mm`);
  }

  if (vals.representative_name?.trim() && updated.includes('[Representative Name]')) {
    updated = updated.split('[Representative Name]').join(vals.representative_name.trim());
  }

  if (vals.total_boxes?.trim()) {
    const tb = vals.total_boxes.trim();
    if (updated.includes('[Total Boxes]')) {
      updated = updated.split('[Total Boxes]').join(tb);
    }
    if (updated.includes('[Total Cartons]')) {
      updated = updated.split('[Total Cartons]').join(tb);
    }
  }

  if (vals.sample_boxes?.trim() && updated.includes('[Sample Boxes]')) {
    updated = updated.split('[Sample Boxes]').join(vals.sample_boxes.trim());
  }

  const nCount = vals.n_count?.trim() || (vals.counts_count ? vals.counts_count.match(/\d+/)?.[0] : '') || (vals.sizes_count ? vals.sizes_count.match(/\d+/)?.[0] : '') || '';
  if (nCount) {
    if (updated.includes('[N] counts')) {
      updated = updated.split('[N] counts').join(`${nCount} counts`);
    }
    if (updated.includes('[N] sizes')) {
      updated = updated.split('[N] sizes').join(`${nCount} sizes`);
    }
    if (updated.includes('[N]')) {
      updated = updated.split('[N]').join(nCount);
    }
  } else {
    if (vals.counts_count?.trim() && updated.includes('[N] counts')) {
      updated = updated.split('[N] counts').join(vals.counts_count.trim());
    }
    if (vals.sizes_count?.trim() && updated.includes('[N] sizes')) {
      updated = updated.split('[N] sizes').join(vals.sizes_count.trim());
    }
  }

  if (vals.container_no?.trim() && updated.includes('[Container No.]')) {
    updated = updated.split('[Container No.]').join(vals.container_no.trim());
  }

  return updated;
}




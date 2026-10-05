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

  const polRow = rows.find((r: any) => /port\s+of\s+loading|loading\s+port|origin\s+port/i.test(r.label || ''));
  const polVal = real(polRow?.value) || (blockState?.metadata as any)?.shipment?.port_of_loading;
  if (polVal) {
    let normPol = normalizePort(polVal);
    if (!/port/i.test(normPol)) {
      normPol = normPol.includes(',') ? normPol.replace(',', ' Port,') : `${normPol} Port`;
    }
    values.port_of_loading = normPol;
    values.origin_port = normPol;
  }

  const voyageRow = rows.find((r: any) => /voyage\s+as\s+per\s+b\/l|port\s+of\s+discharge/i.test(r.label || ''));
  const voyageVal = real(voyageRow?.value);
  if (voyageVal) {
    let port = voyageVal;
    if (/\bto\b/i.test(voyageVal)) {
      const parts = voyageVal.split(/\bto\b/i);
      port = parts[parts.length - 1].trim();
      const origin = parts[0].trim();
      if (origin && !values.port_of_loading) {
        let normOrigin = normalizePort(origin);
        if (!/port/i.test(normOrigin)) {
          normOrigin = normOrigin.includes(',') ? normOrigin.replace(',', ' Port,') : `${normOrigin} Port`;
        }
        values.port_of_loading = normOrigin;
        values.origin_port = normOrigin;
      }
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
      : subject.includes('ambient') || subject.includes('cold room') || subject.includes('room temp') || subject.includes('storage')
      ? 'room_temp'
      : null;
    if (!key) continue;
    if (key === 'room_temp') {
      const val = real(row.min) || real(row.value);
      if (val) values.room_temp = val;
    } else {
      if (real(row.min)) values[`${key}_min`] = real(row.min);
      if (real(row.max)) values[`${key}_max`] = real(row.max);
    }
  }

  const roomNo = (blockState?.metadata as any)?.room_no ||
    rows.find((r: any) => /room\s*(?:no|number)/i.test(r.label || ''))?.value;
  if (roomNo && String(roomNo).trim()) {
    values.room_no = String(roomNo).trim();
  }

  // The carrying temperature from the B/L / air waybill, once the documents are applied.
  const requested = blockState?.metadata?.shipment?.requested_temperature_c;
  if (Array.isArray(requested) ? requested.length : requested !== undefined && requested !== null && requested !== '') {
    (values as any).requested_temp = Array.isArray(requested) ? requested[0] : requested;
    values.set_temp = String((values as any).requested_temp);
  }

  // Temperature recorders summary extracted from blockState
  const recBlock = blocks.find((b) => b.type === 'temperature_recorders');
  const recList: any[] = (recBlock?.recorders || (blockState?.metadata as any)?.shipment?.recorders || []).filter(
    (r: any) => r.included !== false
  );
  if (recList.length > 0) {
    (values as any).recorders = recList;
    const first = recList[0];
    const devId = first.device_id || first.asset_id;
    if (devId) {
      values.device_id = String(devId);
      values.serial_no = String(devId);
      values.imei_no = String(devId);
    }
    if (first.trip_length) values.trip_length = String(first.trip_length);
    if (first.average_c !== undefined && first.average_c !== null && first.average_c !== '') {
      values.avg_temp = String(first.average_c);
    }
    if (first.lowest_c !== undefined && first.lowest_c !== null && first.lowest_c !== '') {
      values.min_temp = String(first.lowest_c);
    }
    if (first.highest_c !== undefined && first.highest_c !== null && first.highest_c !== '') {
      values.max_temp = String(first.highest_c);
    }
    if (first.mkt_c !== undefined && first.mkt_c !== null && first.mkt_c !== '') {
      values.mkt_c = String(first.mkt_c);
    }
  }
  const setPoint = recBlock?.set_point_c;
  if (setPoint !== undefined && setPoint !== null && setPoint !== '') {
    values.set_temp = Array.isArray(setPoint) ? String(setPoint[0]) : String(setPoint);
  }

  // Defects actually counted: columns with a figure above zero in any row.
  const defects: string[] = [];
  const tables = blocks.filter((b) => b.type === 'table');
  let sampleBoxCount = 0;
  const countSet = new Set<string>();

function isPlaceholderValue(val: any): boolean {
  if (val === undefined || val === null) return true;
  const s = String(val).trim();
  if (!s || s === '-' || s === '–') return true;
  if (s.startsWith('[') && s.endsWith(']')) return true;
  if (/^(?:count\s*\/\s*size|size\s*\/\s*count|information not furnished|n\/a)$/i.test(s)) return true;
  return false;
}

function cleanVarietyName(varName: string): string {
  if (!varName) return '';
  let v = varName.trim();
  if (isPlaceholderValue(v)) return '';
  // Strip repeated 'fresh' prefixes (e.g. 'Fresh Fresh Apple' -> 'Apple')
  v = v.replace(/^(?:fresh\s+)+/i, '');
  if (/granny\s*smith|granny/i.test(v)) return 'Granny';
  if (/royal\s*gala/i.test(v)) return v.includes('NZ') ? 'NZ Fresh Apples / Royal Gala' : 'Royal Gala';
  if (/forelle|frl/i.test(v)) return 'FRL';
  if (/vermont|vbt/i.test(v)) return 'VBT';
  if (/packham/i.test(v)) return 'Packham';
  if (/abate/i.test(v)) return 'Abate';
  if (/pink\s*lady/i.test(v)) return 'Pink Lady';
  if (/red\s*delicious/i.test(v)) return 'Red Delicious';
  if (/fuji/i.test(v)) return 'Fuji';

  // If it's just the generic fruit name alone, return empty string
  if (/^(?:apple|pear|mandarin|grapes?|plum|orange|kiwi)s?$/i.test(v)) {
    return '';
  }

  // Strip leading fruit names if it's e.g. "Apple Cripps Pink"
  v = v.replace(/^(?:apple|pear|mandarin|grapes?|plum)s?\s*[-–/:]?\s*/i, '');
  return v.trim();
}

function isSubtotalRow(row: any, precedingRows: any[]): boolean {
  if (row.is_subtotal || row.is_grand_total) return true;
  const grp = String(row.group || '').toLowerCase();
  if (grp.includes('total') || grp.includes('subtotal') || grp.includes('sum') || grp.includes('percentage')) {
    return true;
  }
  if (row.boxes_opened === 1) return false;
  if (precedingRows.length === 0) return false;
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
      let openedSum = 0;
      let nonSubtotalCount = 0;
      for (const r of tableRows) {
        const isSub = isSubtotalRow(r, preceding);
        preceding.push(r);
        if (isSub) continue;

        nonSubtotalCount++;
        if (r.boxes_opened && Number(r.boxes_opened) > 0) {
          openedSum += Number(r.boxes_opened);
        }

        const cVal = r.group ?? r.count ?? r.size ?? r.counts ?? r.puc;
        if (!isPlaceholderValue(cVal)) {
          const raw = String(cVal).trim();
          const n = parseInt(raw, 10);
          if (!isNaN(n) && n > 0) {
            // Standard fruit count numbers are <= 250 (e.g. 100, 120, 150, 165, 180, 198)
            // Numbers > 250 (e.g. 900, 825) are carton pieces subtotal rows, not count sizes.
            if (n <= 250) {
              countSet.add(String(n));
            }
          } else if (!isPlaceholderValue(raw)) {
            countSet.add(raw);
          }
        }
      }
      if (openedSum > 0) {
        sampleBoxCount += openedSum;
      } else {
        sampleBoxCount += nonSubtotalCount;
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
        if (!isPlaceholderValue(sVal)) {
          const raw = String(sVal).trim();
          const n = parseInt(raw, 10);
          if (!isNaN(n) && n > 0) {
            if (n <= 250) {
              countSet.add(String(n));
            }
          } else if (!isPlaceholderValue(raw)) {
            countSet.add(raw);
          }
        }
      }
    }
  }

  if (sampleBoxCount > 0) {
    values.sample_boxes = String(sampleBoxCount);
  }

  // Extract overall commodity variety from Particulars rows or Commodity Description
  let defaultVariety = '';
  const descRow = rows.find((r: any) => /commodity|variety|nature\s+of\s+cargo|description/i.test(r.label || ''));
  const descVal = real(descRow?.value) || (blockState?.metadata as any)?.shipment?.commodity_description || '';
  if (descVal) {
    if (/granny\s*smith|granny/i.test(descVal)) defaultVariety = 'Granny';
    else if (/royal\s*gala/i.test(descVal)) defaultVariety = descVal.includes('NZ') ? 'NZ Fresh Apples / Royal Gala' : 'Royal Gala';
    else if (/forelle/i.test(descVal) && /vermont/i.test(descVal)) defaultVariety = 'Forelle / Vermont Beauty';
    else if (/forelle|frl/i.test(descVal)) defaultVariety = 'FRL';
    else if (/vermont|vbt/i.test(descVal)) defaultVariety = 'VBT';
    else if (/packham/i.test(descVal)) defaultVariety = 'Packham';
    else if (/pink\s*lady/i.test(descVal)) defaultVariety = 'Pink Lady';
    else if (/red\s*delicious/i.test(descVal)) defaultVariety = 'Red Delicious';
    else if (/fuji/i.test(descVal)) defaultVariety = 'Fuji';
  }
  if (defaultVariety) {
    values.variety = defaultVariety;
  }

  // 1. Build consignment count items & map from Particulars Consignment table(s) (from top uploaded documents)
  const consignmentCountMap = new Map<string, string>();
  const consignmentItems: Array<{ count: string; variety: string }> = [];
  const seenConsignmentKeys = new Set<string>();

  const allConsignmentTables = rows.filter((r: any) =>
    r.type === 'table' ||
    Boolean(r.headers) ||
    ((r.label || '').toLowerCase().includes('consignment') && (Boolean(r.rows) || Boolean(r.items)))
  );
  for (const ct of allConsignmentTables) {
    const subItems: any[] = ct.rows || ct.items || [];
    for (const it of subItems) {
      const cVal = it.col2 ?? it.size ?? it.count ?? it.sizes ?? it.counts;
      const vVal = it.col1 ?? it.variety ?? it.commodity ?? defaultVariety;
      if (!isPlaceholderValue(cVal)) {
        const rawCount = String(cVal).trim().match(/\d+/)?.[0] || String(cVal).trim();
        const rawVarStr = isPlaceholderValue(vVal) ? defaultVariety : String(vVal);
        const cleanedVar = cleanVarietyName(rawVarStr);
        if (rawCount && !consignmentCountMap.has(rawCount)) {
          consignmentCountMap.set(rawCount, cleanedVar);
        }
        const key = `${cleanedVar}_${rawCount}`;
        if (!seenConsignmentKeys.has(key)) {
          seenConsignmentKeys.add(key);
          consignmentItems.push({ count: rawCount, variety: cleanedVar });
        }
      }
    }
  }

  // 2. From Defect Table (b_table) sampled rows:
  const defectItems: Array<{ count: string; variety: string }> = [];
  const seenDefectKeys = new Set<string>();

  for (const table of tables) {
    const tableRows = table.rows || [];
    const preceding: any[] = [];
    for (const r of tableRows) {
      const isSub = isSubtotalRow(r, preceding);
      preceding.push(r);
      if (isSub) continue;
      const rawGroup = String(r.group ?? r.count ?? r.size ?? r.counts ?? '').trim();
      if (!rawGroup || isPlaceholderValue(rawGroup)) continue;

      let rowVar = defaultVariety;
      let rowCount = '';
      if (/forelle|frl/i.test(rawGroup)) {
        rowVar = 'FRL';
        rowCount = rawGroup.match(/\d+/)?.[0] || '';
      } else if (/vermont|vbt/i.test(rawGroup)) {
        rowVar = 'VBT';
        rowCount = rawGroup.match(/\d+/)?.[0] || '';
      } else if (/packham/i.test(rawGroup)) {
        rowVar = 'Packham';
        rowCount = rawGroup.match(/\d+/)?.[0] || '';
      } else {
        const numMatch = rawGroup.match(/\b\d{2,3}\b/);
        if (numMatch) {
          rowCount = numMatch[0];
          const nonDigits = rawGroup.replace(/\d+/g, '').replace(/[-–/():]/g, '').trim();
          if (nonDigits) {
            rowVar = cleanVarietyName(nonDigits);
          } else if (consignmentCountMap.has(rowCount)) {
            rowVar = consignmentCountMap.get(rowCount)!;
          }
        }
      }

      if (rowCount && Number(rowCount) <= 250) {
        if (!rowVar && consignmentCountMap.has(rowCount)) {
          rowVar = consignmentCountMap.get(rowCount)!;
        }
        const key = `${rowVar}_${rowCount}`;
        if (!seenDefectKeys.has(key)) {
          seenDefectKeys.add(key);
          defectItems.push({ count: rowCount, variety: rowVar });
        }
      }
    }
  }

  // Priority: defect table sampled counts (actual boxes opened) > consignment table (top documents) > countSet
  let countItems: Array<{ count: string; variety: string; min?: string; max?: string }> = [];
  if (defectItems.length > 0) {
    countItems = defectItems;
  } else if (consignmentItems.length > 0) {
    countItems = consignmentItems;
  } else if (countSet.size > 0) {
    for (const c of countSet) {
      countItems.push({ count: c, variety: defaultVariety });
    }
  }

  if (countItems.length > 0) {
    values.n_count = String(countItems.length);
    values.counts_count = countItems.length === 1 ? '1 count' : `${countItems.length} counts`;
    values.sizes_count = countItems.length === 1 ? '1 size' : `${countItems.length} sizes`;
  } else if (countSet.size > 0) {
    values.n_count = String(countSet.size);
    values.counts_count = countSet.size === 1 ? '1 count' : `${countSet.size} counts`;
    values.sizes_count = countSet.size === 1 ? '1 size' : `${countSet.size} sizes`;
  }

  // Attach per-count pressure readings if available (e.g. from tally sheet extraction)
  const pReadings: any[] = (blockState?.metadata as any)?.pressure_readings || [];
  for (const ci of countItems) {
    const ciDigits = ci.count.replace(/\D/g, '');
    // 1. Try matching both count and variety
    let match = pReadings.find((pr: any) => {
      const prDigits = String(pr.count || '').replace(/\D/g, '');
      const cMatch =
        (prDigits && ciDigits && prDigits === ciDigits) ||
        String(pr.count || '').trim().toLowerCase() === ci.count.trim().toLowerCase();
      if (!cMatch) return false;
      if (pr.variety && ci.variety) {
        return cleanVarietyName(String(pr.variety)) === cleanVarietyName(ci.variety);
      }
      return false;
    });
    // 2. Fallback to count alone if no exact variety match
    if (!match) {
      match = pReadings.find((pr: any) => {
        const prDigits = String(pr.count || '').replace(/\D/g, '');
        return (
          (prDigits && ciDigits && prDigits === ciDigits) ||
          String(pr.count || '').trim().toLowerCase() === ci.count.trim().toLowerCase()
        );
      });
    }
    if (match && match.min !== undefined && match.max !== undefined) {
      ci.min = String(match.min);
      ci.max = String(match.max);
    }
  }
  (values as any).count_items = countItems;

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
  let detectedCommodity = meta.commodity ? String(meta.commodity).toLowerCase().trim().replace(/s$/, '') : undefined;
  if (!detectedCommodity && blockState?.report_title) {
    const title = String(blockState.report_title);
    const titleMatch = title.match(/\b(APPLE|PEAR|PLUM|GRAPES?|MANDARINS?|ORANGE|KIWI|MANGO|BANANA)\b/i);
    if (titleMatch) {
      detectedCommodity = titleMatch[1].toLowerCase().replace(/s$/, '');
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
  const countsCount = nCount === '1' ? '1 count' : nCount ? `${nCount} counts` : (vals.counts_count?.trim() || '[N] counts');
  const pulpMin = vals.pulp_min?.trim();
  const pulpMax = vals.pulp_max?.trim();
  const pulpRange = pulpMin && pulpMax ? `${pulpMin}°C to ${pulpMax}°C` : '[Pulp Temp Min °C] to [Pulp Temp Max °C]';

  const countItems: Array<{ count: string; variety?: string; min?: string; max?: string }> =
    (vals as any).count_items || [];

  let pressureBullets = '';
  if (countItems.length > 0) {
    pressureBullets = countItems
      .map((ci) => {
        const vName = ci.variety ? `${ci.variety} (${ci.count} Count)` : `(${ci.count} Count)`;
        const range =
          ci.min && ci.max
            ? `Range of ${ci.min} LBS to ${ci.max} LBS.`
            : vals.pressure_min && vals.pressure_max
            ? `Range of ${vals.pressure_min} LBS to ${vals.pressure_max} LBS.`
            : `Range of [${ci.count} Count Pressure Min LBS] to [${ci.count} Count Pressure Max LBS].`;
        return `• ${vName}: ${range}`;
      })
      .join('\n');
  } else {
    const pressMin = vals.pressure_min?.trim();
    const pressMax = vals.pressure_max?.trim();
    const pressRange =
      pressMin && pressMax
        ? `Range of ${pressMin} LBS to ${pressMax} LBS.`
        : 'Range of [Fruit Pressure Min LBS] to [Fruit Pressure Max LBS].';
    const appleVar = vals.variety?.trim()
      ? `${vals.variety.trim()} ([Count] Count)`
      : '[Apple Variety] ([Count] Count)';
    pressureBullets = `• ${appleVar}: ${pressRange}`;
  }

  const brixMin = vals.brix_min?.trim();
  const brixMax = vals.brix_max?.trim();
  const brixRange = brixMin && brixMax ? `${brixMin}% to ${brixMax}%` : '[Brix Min %] to [Brix Max %]';

  const sampleBoxes = vals.sample_boxes?.trim() || '[Sample Boxes]';
  const roomNo = vals.room_no?.trim() || '[Room No.]';
  const roomTemp = vals.room_temp?.trim() ? `${vals.room_temp.trim()}°C` : '[Room Temp °C]';

  return (
    `The consignee's end buyer representative, ${rep}, presented ${totalBoxes} boxes across ${countsCount} on various pallets for our survey. ` +
    `These were stored in cold storage room number ${roomNo}, where the ambient temperature was recorded as ${roomTemp}.\n\n` +
    `THE CONDITION FOUND OF APPLE FRUITS:\n\n` +
    `The pulp temperature of the Apple fruits was measured inside the cold room using a digital thermometer and registered in the range of ${pulpRange}.\n\n` +
    `From different locations within the cold room, ${sampleBoxes} boxes across ${countsCount} were randomly selected and opened for detailed examination. ` +
    `Upon unpacking and inspection, the Apple fruits inside the cartons exhibited a mixture of conditions, including sound, and various degrees of rotten.\n\n` +
    `The pressure of the randomly selected various Apple fruits across ${countsCount} were measured using a penetrometer, and the following average values were recorded for the sound apples:\n` +
    `${pressureBullets}\n\n` +
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
  const countsCount = nCount === '1' ? '1 count' : nCount ? `${nCount} counts` : (vals.counts_count?.trim() || '[N] counts');
  const pulpMin = vals.pulp_min?.trim();
  const pulpMax = vals.pulp_max?.trim();
  const pulpRange = pulpMin && pulpMax ? `${pulpMin}°C to ${pulpMax}°C` : '[Pulp Temp Min °C] to [Pulp Temp Max °C]';

  const countItems: Array<{ count: string; variety?: string; min?: string; max?: string }> =
    (vals as any).count_items || [];

  let pressureBullets = '';
  if (countItems.length > 0) {
    pressureBullets = countItems
      .map((ci, idx) => {
        const vName = ci.variety ? `${ci.variety} (${ci.count} Count)` : `(${ci.count} Count)`;
        const range =
          ci.min && ci.max
            ? `Range of ${ci.min} LBS to ${ci.max} LBS.`
            : vals.pressure_min && vals.pressure_max
            ? `Range of ${vals.pressure_min} LBS to ${vals.pressure_max} LBS.`
            : `Range of [${ci.count} Count Pressure Min LBS] to [${ci.count} Count Pressure Max LBS].`;
        return `${idx + 1}) ${vName}: ${range}`;
      })
      .join('\n');
  } else {
    const pressMin = vals.pressure_min?.trim();
    const pressMax = vals.pressure_max?.trim();
    const pressRange =
      pressMin && pressMax
        ? `Range of ${pressMin} LBS to ${pressMax} LBS.`
        : 'Range of [Fruit Pressure Min LBS] to [Fruit Pressure Max LBS].';
    const pearVar = vals.variety?.trim()
      ? `${vals.variety.trim()} ([Count] Count)`
      : '[Pear Variety] ([Count] Count)';
    pressureBullets = `1) ${pearVar}: ${pressRange}`;
  }

  const brixMin = vals.brix_min?.trim();
  const brixMax = vals.brix_max?.trim();
  const brixRange = brixMin && brixMax ? `${brixMin}% to ${brixMax}%` : '[Brix Min %] to [Brix Max %]';

  const sampleBoxes = vals.sample_boxes?.trim() || '[Sample Boxes]';
  const roomNo = vals.room_no?.trim() || '[Room No.]';
  const roomTemp = vals.room_temp?.trim() ? `${vals.room_temp.trim()}°C` : '[Room Temp °C]';

  return (
    `The consignee's representative, ${rep}, presented ${totalBoxes} boxes across ${countsCount} for our survey. ` +
    `These were stored in cold storage room number ${roomNo}, where the ambient temperature was recorded as ${roomTemp}.\n\n` +
    `THE CONDITION FOUND OF PEAR FRUITS:\n\n` +
    `The pulp temperature of the Pear fruits was measured inside the cold room using a digital thermometer and registered in the range of ${pulpRange}.\n\n` +
    `From different locations within the cold room, ${sampleBoxes} boxes across ${countsCount} were randomly selected and opened for detailed examination. ` +
    `Upon unpacking and inspection, the Pear fruits inside the cartons exhibited a mixture of conditions, including sound and in a rotten condition in various degrees.\n\n` +
    `The pressure of the Pear fruits under ${countsCount} was measured using a penetrometer, and the following average values were recorded for the sound Pears:\n` +
    `${pressureBullets}\n\n` +
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
  const roomNo = vals.room_no?.trim() || '[Room No.]';
  const roomTemp = vals.room_temp?.trim() ? `${vals.room_temp.trim()}°C` : '[Room Temp °C]';

  return (
    `The consignees’ representative ${rep}, produced before us the ${totalBoxes} cartons under ${sizesCount} for our survey, ` +
    `stored inside the cold storage no. ${roomNo}. Cold room display temperature was found maintained at ${roomTemp}.\n\n` +
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
  if (pressMin && updated.includes('[Fruit Pressure Min LBS]')) {
    updated = updated.split('[Fruit Pressure Min LBS]').join(pressMin);
  }
  if (pressMax && updated.includes('[Fruit Pressure Max LBS]')) {
    updated = updated.split('[Fruit Pressure Max LBS]').join(pressMax);
  }

  const countItems: Array<{ count: string; variety?: string; min?: string; max?: string }> =
    (vals as any).count_items || [];
  if (countItems.length > 0) {
    const isPear = /pear/i.test(updated);
    const bullets = countItems
      .map((ci, idx) => {
        const vName = ci.variety ? `${ci.variety} (${ci.count} Count)` : `(${ci.count} Count)`;
        const range =
          ci.min && ci.max
            ? `Range of ${ci.min} LBS to ${ci.max} LBS.`
            : vals.pressure_min && vals.pressure_max
            ? `Range of ${vals.pressure_min} LBS to ${vals.pressure_max} LBS.`
            : `Range of [${ci.count} Count Pressure Min LBS] to [${ci.count} Count Pressure Max LBS].`;
        return isPear ? `${idx + 1}) ${vName}: ${range}` : `• ${vName}: ${range}`;
      })
      .join('\n');

    const placeholders = [
      /^[•\d\)]*\s*\[Apple Variety\]\s*\(\[Count\]\s*Count\):\s*Range of \[Fruit Pressure Min LBS\] to \[Fruit Pressure Max LBS\]\./m,
      /^[•\d\)]*\s*\[Pear Variety\]\s*\(\[Count\]\s*Count\):\s*Range of \[Fruit Pressure Min LBS\] to \[Fruit Pressure Max LBS\]\./m,
      /^[•\d\)]*\s*Range of \[Fruit Pressure Min LBS\] to \[Fruit Pressure Max LBS\]\./m,
    ];
    for (const ph of placeholders) {
      if (ph.test(updated)) {
        updated = updated.replace(ph, bullets);
        break;
      }
    }

    for (const ci of countItems) {
      const phRange = `[${ci.count} Count Pressure Min LBS] to [${ci.count} Count Pressure Max LBS]`;
      const pMin = ci.min || vals.pressure_min;
      const pMax = ci.max || vals.pressure_max;
      if (pMin && pMax && updated.includes(phRange)) {
        updated = updated.split(phRange).join(`${pMin} LBS to ${pMax} LBS`);
      }
      const phMin = `[${ci.count} Count Pressure Min LBS]`;
      if (pMin && updated.includes(phMin)) {
        updated = updated.split(phMin).join(pMin);
      }
      const phMax = `[${ci.count} Count Pressure Max LBS]`;
      if (pMax && updated.includes(phMax)) {
        updated = updated.split(phMax).join(pMax);
      }
    }
  }

  // Also replace any generic or remaining count pressure placeholders if overall pressure is available
  if (vals.pressure_min && vals.pressure_max) {
    updated = updated.replace(
      /\[[^\s\]]+ Count Pressure Min LBS\] to \[[^\s\]]+ Count Pressure Max LBS\]/g,
      `${vals.pressure_min} LBS to ${vals.pressure_max} LBS`
    );
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

  if (vals.room_no?.trim() && updated.includes('[Room No.]')) {
    updated = updated.split('[Room No.]').join(vals.room_no.trim());
  }

  if (vals.room_temp?.trim() && updated.includes('[Room Temp °C]')) {
    updated = updated.split('[Room Temp °C]').join(`${vals.room_temp.trim()}°C`);
  }

  if (vals.container_no?.trim() && updated.includes('[Container No.]')) {
    updated = updated.split('[Container No.]').join(vals.container_no.trim());
  }

  return updated;
}

// ============================================================================
// PARAGRAPH 3: CAUSE OF LOSS & TEMPERATURE RECORDERS (Apple, Pear, Mandarin, Grapes, Plum)
// ============================================================================

export type CauseCondition = 'carrier_breach' | 'cold_chain_complied' | 'no_recorder_data';

/**
 * Auto-detects the initial legal condition from uploaded documents and recorder readings.
 */
export function detectCauseCondition(clauseContext: ClauseContext, block?: any): CauseCondition {
  if (block?.cause_condition) {
    return block.cause_condition as CauseCondition;
  }
  const vals = clauseContext.values || {};
  const recs: any[] = (vals as any).recorders || [];
  if (!recs || recs.length === 0) {
    return 'no_recorder_data';
  }
  const setTemp = parseFloat(vals.set_temp || (vals as any).requested_temp || '0');
  const avgTemp = parseFloat(vals.avg_temp || '0');
  const maxTemp = parseFloat(vals.max_temp || '0');
  const mkt = parseFloat(vals.mkt_c || '0');
  // Breach if average or MKT is > 1.5°C above setpoint, or peak is > 5.5°C
  if (avgTemp - setTemp > 1.5 || mkt - setTemp > 2.0 || maxTemp > 5.5) {
    return 'carrier_breach';
  }
  return 'cold_chain_complied';
}

/**
 * Builds authentic Paragraph 3 Preamble (Carriage requested temperature & recorder intake).
 */
export function buildParagraph3Preamble(clauseContext: ClauseContext): string {
  const vals = clauseContext.values || {};
  const commodity = (clauseContext.commodity || 'Fruit').trim();
  const capCommodity = commodity.charAt(0).toUpperCase() + commodity.slice(1).toLowerCase();
  const containerList: string[] = (vals as any).container_nos || (vals.container_no ? [vals.container_no] : []);
  const isMulti = containerList.length > 1;

  if (isMulti) {
    return (
      `As per the Bill of Lading, the requested temperature for this shipment of fresh ${capCommodity} was [Set Temp]°C. ` +
      `In the course of our investigation, we were provided with the downloaded temperature recorders installed inside the containers. ` +
      `Reference of the recorders was made in the transport documents. Examination of the printouts revealed the following.`
    );
  }

  return (
    `As per the Bill of Lading, the requested temperature for this shipment of fresh ${capCommodity} was [Set Temp]°C. ` +
    `In the course of our investigation, we were provided with the downloaded temperature recorder installed inside the container. ` +
    `Reference of the recorder was made in the transport documents. Examination of the printouts revealed the following.`
  );
}

/**
 * Builds Paragraph 3 Cause of Loss for Apple (Reports M-161, M-164).
 */
export function buildAppleCauseOfLoss(clauseContext: ClauseContext, condition: CauseCondition = 'carrier_breach'): string {
  const vals = clauseContext.values || {};
  const containerList: string[] = (vals as any).container_nos || (vals.container_no ? [vals.container_no] : []);

  if (condition === 'carrier_breach') {
    return (
      `CAUSE OF LOSS:\n\n` +
      `The direct and proximate cause of the loss was sustained thermal abuse and cold-chain failure during transit.\n\n` +
      `Carriage Instructions: As per the governing Bill of Lading [Bill of Lading No.], the carrier was instructed to carry this consignment of Fresh Apples strictly at [Set Temp]°C throughout the voyage.\n\n` +
      `• Temperature Breach: Data logger records demonstrate that this required set point was never maintained, registering an average temperature of [Avg Temp]°C with peaks reaching [Max Temp]°C. This substantial and continuous deviation proves the cargo suffered prolonged temperature abuse while in the carrier's custody.\n\n` +
      `• Biological Effect: This continuous exposure to elevated temperatures accelerated the Apple fruits' metabolic respiration and ethylene production, leading to premature flesh softening, internal breakdown, and rapid progression of rot and decay.\n\n` +
      `• Conclusion on Liability: The primary cause of loss is transit temperature abuse resulting directly from the carrier's failure to maintain the contracted [Set Temp]°C setting, rendering the affected lot commercially unmerchantable and unfit for human consumption.`
    );
  }

  if (condition === 'cold_chain_complied') {
    const cRef = containerList.length > 1
      ? `Reefer containers ${containerList.join(' & ')}`
      : (containerList.length === 1 ? `Reefer container ${containerList[0]}` : 'Reefer container [Container No.]');
    return (
      `Findings & Assessment:\n\n` +
      `Refrigeration Integrity: ${cRef} maintained continuous cold-chain compliance throughout transit from [Port of Loading] to [Port of Discharge]. ` +
      `Data records show a steady average of [Avg Temp]°C against the [Set Temp]°C setpoint with zero transit alarm triggers. The spike to [Max Temp]°C occurred solely post gate-out during destuffing and ambient exposure.\n\n` +
      `Proximate Cause: Because reefer equipment operated without mechanical failure or transit temperature abuse, the cargo damage cannot be attributed to carrier mishandling or transit refrigeration breakdown. ` +
      `The deterioration observed is attributable to inherent vice, pre-harvest factors (such as latent orchard conditions), or natural senescence.\n\n` +
      `As an act to mitigate the loss, we advised the consignees to sell the cargo as soon as possible to avoid further damages to Apple fruits.`
    );
  }

  // Condition 3: no_recorder_data (authentic M-161 & M-164 wording)
  const cRef = containerList.length > 1 ? `the subject containers` : `the subject container`;
  const serialSlot = containerList.length > 1 ? `(Serial Nos. [Serial Nos.])` : `(Serial No. [Serial No.])`;
  return (
    `According to the Bill of Lading, the requested temperature for this shipment of fresh Apple fruits was [Set Temp]°C. ` +
    `During our investigation, the Consignees informed us that they were unable to download the data from the temperature recorder ${serialSlot} ` +
    `installed inside ${cRef}. Consequently, we are unable to comment on any potential temperature anomalies that may have occurred during transit.\n\n` +
    `Based on our physical survey findings and taking the above into consideration, we conclude as follows:\n\n` +
    `We are of the opinion that the fresh Apple fruits likely sustained damage (shriveled and the rotten) due to temperature variations occurring during the transit and/or pre-shipment stages. ` +
    `However, the precise stage at which the deterioration commenced cannot be definitively established due to the unavailability of the temperature data log.\n\n` +
    `Additional contributing factors observed during the inspection include:\n` +
    `• Mechanical injury, likely sustained during automated sorting or grading processes.\n` +
    `• Pressure damage (bruising) indicative of improper harvesting and handling.\n` +
    `• Pre-harvest defects, such as russet and the less-colour.`
  );
}

/**
 * Builds Paragraph 3 Cause of Loss for Pear (Reports M-162, M-163).
 */
export function buildPearCauseOfLoss(clauseContext: ClauseContext, condition: CauseCondition = 'carrier_breach'): string {
  const vals = clauseContext.values || {};
  const containerList: string[] = (vals as any).container_nos || (vals.container_no ? [vals.container_no] : []);

  if (condition === 'carrier_breach') {
    return (
      `CAUSE OF LOSS:\n\n` +
      `The direct and proximate cause of the loss was sustained thermal abuse and cold-chain failure during transit.\n\n` +
      `Carriage Instructions: As per the governing Bill of Lading [Bill of Lading No.], the carrier was instructed to carry this consignment of Fresh Pears strictly at [Set Temp]°C throughout the voyage.\n\n` +
      `• Temperature Breach: Datalogger records confirm that the carrier failed to maintain this required temperature, registering an average temperature of [Avg Temp]°C with peak temperatures reaching [Max Temp]°C. This substantial and continuous deviation proves the cargo suffered prolonged temperature abuse while in the carrier's custody.\n\n` +
      `• Biological Effect: This continuous exposure to elevated transit temperatures accelerated the Pear fruits' metabolic respiration and ethylene synthesis, triggering premature ripening, extensive flesh softening, core breakdown, and rapid fungal rot across the affected consignment.\n\n` +
      `• Conclusion on Liability: The primary cause of loss is transit temperature abuse resulting directly from the carrier's failure to maintain the contracted [Set Temp]°C setting, rendering the affected lot commercially unmerchantable and unfit for human consumption.`
    );
  }

  if (condition === 'cold_chain_complied') {
    const cRef = containerList.length > 1
      ? `Reefer containers ${containerList.join(' & ')}`
      : (containerList.length === 1 ? `Reefer container ${containerList[0]}` : 'Reefer container [Container No.]');
    return (
      `Findings & Assessment:\n\n` +
      `Refrigeration Integrity: ${cRef} maintained continuous cold-chain compliance throughout transit from [Port of Loading] to [Port of Discharge]. ` +
      `Data records show a steady average of [Avg Temp]°C against the [Set Temp]°C setpoint with zero transit alarm triggers. The spike to [Max Temp]°C occurred solely post gate-out during destuffing and ambient exposure.\n\n` +
      `Proximate Cause: As the carrier's reefer machinery functioned continuously without mechanical failure or thermal abuse, transit temperature breach is ruled out. ` +
      `The deterioration observed is attributable to pre-shipment storage duration, post-harvest senescence, or latent fungal infection.\n\n` +
      `As an act to mitigate the loss, we advised the consignees to sell the cargo as soon as possible to avoid further damages to Pear fruits.`
    );
  }

  // Condition 3: no_recorder_data (authentic M-162 & M-163 wording)
  const cRef = containerList.length > 1 ? `the subject containers` : `the subject container`;
  const imeiSlot = containerList.length > 1 ? `(IMEI Nos. [IMEI Nos.])` : `(IMEI No. [IMEI No.])`;
  return (
    `According to the Bill of Lading, the requested temperature for this shipment of fresh Pear fruits was [Set Temp]°C. ` +
    `During our investigation, the Consignees informed us that they were unable to download the data from the temperature recorder ${imeiSlot} ` +
    `installed inside ${cRef}. Consequently, we are unable to comment on any potential temperature anomalies that may have occurred during transit.\n\n` +
    `Based on our physical survey findings and taking the above into consideration, we conclude as follows:\n\n` +
    `We are of the opinion that the fresh Pear fruits likely sustained damage (rotten) due to temperature variations occurring during the transit and/or pre-shipment stages. ` +
    `However, the precise stage at which the deterioration commenced cannot be definitively established due to the unavailability of the temperature data log.\n\n` +
    `Additional contributing factors observed during the inspection include:\n` +
    `• Friction marking and surface blemishes indicative of handling.\n` +
    `• Natural physiological senescence.`
  );
}

/**
 * Builds Paragraph 3 Cause of Loss for Mandarin (Reports M-165, M-166).
 */
export function buildMandarinCauseOfLoss(clauseContext: ClauseContext, condition: CauseCondition = 'cold_chain_complied'): string {
  const vals = clauseContext.values || {};
  const containerList: string[] = (vals as any).container_nos || (vals.container_no ? [vals.container_no] : []);

  if (condition === 'carrier_breach') {
    return (
      `CAUSE OF LOSS:\n\n` +
      `The direct and proximate cause of the loss was sustained thermal abuse and cold-chain failure during transit.\n\n` +
      `Carriage Instructions: As per the governing Bill of Lading [Bill of Lading No.], the carrier was instructed to carry this consignment of Fresh Mandarins strictly at [Set Temp]°C throughout the voyage.\n\n` +
      `• Temperature Breach: Datalogger records demonstrate that the carrier failed to maintain this required temperature throughout transit, registering an average temperature of [Avg Temp]°C and peak temperatures reaching [Max Temp]°C.\n\n` +
      `• Biological Effect: This continuous exposure to elevated temperatures weakened the rind structure, accelerated moisture loss, and promoted rind breakdown, directly leading to soft/pressed fruits, rot spots, and active green/blue mold (Penicillium spp.) sporulation.\n\n` +
      `• Conclusion on Liability: The primary cause of loss is transit temperature abuse resulting directly from the carrier's failure to maintain the contracted [Set Temp]°C setting, directly causing cargo decay and unmerchantability.`
    );
  }

  if (condition === 'cold_chain_complied') {
    // Authentic M-165 & M-166 wording
    const cRef = containerList.length > 1
      ? `Reefer containers ${containerList.join(' & ')}`
      : (containerList.length === 1 ? `Reefer container ${containerList[0]}` : 'Reefer container [Container No.]');
    const recRef = containerList.length > 1 ? `recorders` : `recorder [Serial No.]`;
    return (
      `Findings & Assessment:\n\n` +
      `Refrigeration Integrity: ${cRef} maintained continuous cold-chain compliance throughout transit from [Port of Loading] to [Port of Discharge] aboard [Vessel Name & Voyage No.]. ` +
      `Data from ${recRef} shows a steady average temperature of [Avg Temp]°C against the [Set Temp]°C setpoint, with no freezing events (minimum [Min Temp]°C) and zero transit alarm triggers. ` +
      `The spike to [Max Temp]°C occurred solely post gate-out during destuffing and ambient exposure.\n\n` +
      `Proximate Cause: Because reefer equipment operated without mechanical failure or transit temperature abuse, the cargo damage cannot be attributed to carrier mishandling or transit refrigeration breakdown. ` +
      `The proximate cause of loss is attributable to inherent vice, pre-shipment factors, and natural post-harvest senescence of the fruit.\n\n` +
      `As an act to mitigate the loss, we advised the consignees to sell the cargo as soon as possible to avoid further damages to Mandarin fruits.`
    );
  }

  // Condition 3: no_recorder_data
  const cRef = containerList.length > 1 ? `the subject containers` : `the subject container`;
  const serialSlot = containerList.length > 1 ? `(Serial Nos. [Serial Nos.])` : `(Serial No. [Serial No.])`;
  return (
    `According to the Bill of Lading, the requested temperature for this shipment of fresh Mandarin fruits was [Set Temp]°C. ` +
    `During our investigation, the Consignees informed us that they were unable to download the data from the temperature recorder ${serialSlot} ` +
    `installed inside ${cRef}. Consequently, we are unable to comment on any potential temperature anomalies that may have occurred during transit.\n\n` +
    `Based on our physical survey findings, we are of the opinion that the fresh Mandarin fruits likely sustained soft/pressed condition, rot spots, ` +
    `and fungal decay due to temperature variations occurring during the transit and/or pre-shipment stages, though the exact onset cannot be definitively fixed without recorder logs.`
  );
}

/**
 * Builds Paragraph 3 Cause of Loss for Grapes (Reports M-167, M-168).
 */
export function buildGrapesCauseOfLoss(clauseContext: ClauseContext, condition: CauseCondition = 'carrier_breach'): string {
  const vals = clauseContext.values || {};
  const containerList: string[] = (vals as any).container_nos || (vals.container_no ? [vals.container_no] : []);

  if (condition === 'carrier_breach') {
    // Authentic M-167 & M-168 wording
    const voyagePeriod = vals.trip_length ? `${vals.trip_length} voyage` : `voyage`;
    return (
      `CAUSE OF LOSS:\n\n` +
      `The direct and proximate cause of the loss was sustained thermal abuse and cold-chain failure during transit.\n\n` +
      `Carriage Instructions: As per the governing Bill of Lading [Bill of Lading No.], the carrier was required to maintain a set temperature of [Set Temp]°C with ventilation throughout the sea voyage.\n\n` +
      `• Temperature Breach: Data logger records demonstrate that this required set point was never achieved at any stage during the ${voyagePeriod}. ` +
      `The recorded minimum was only [Min Temp]°C, with the shipment maintaining an average temperature of [Avg Temp]°C and a Mean Kinetic Temperature (MKT) of [MKT]°C, alongside repeated high-temperature breaches exceeding 8.0°C and terminal spikes reaching [Max Temp]°C.\n\n` +
      `• Biological Effect: Physical survey carried out upon destuffing confirmed that this extended lack of refrigeration caused severe cargo damage, accelerating the fruit's metabolic respiration, moisture loss, and physiological senescence, ` +
      `leading directly to berry softening, rachis browning, watery breakdown, skin slippage, and active nesting of gray mold (Botrytis cinerea).\n\n` +
      `• Conclusion on Liability: The continuous failure of the reefer machinery to deliver the required [Set Temp]°C temperature during transit represents the primary and proximate cause of damage, rendering the cargo commercially depreciated and unfit for normal marketing.`
    );
  }

  if (condition === 'cold_chain_complied') {
    const cRef = containerList.length > 1
      ? `Reefer containers ${containerList.join(' & ')}`
      : (containerList.length === 1 ? `Reefer container ${containerList[0]}` : 'Reefer container [Container No.]');
    return (
      `Findings & Assessment:\n\n` +
      `Refrigeration Integrity: ${cRef} maintained continuous cold-chain compliance throughout transit from [Port of Loading] to [Port of Discharge]. ` +
      `Datalogger records demonstrate that the carrier maintained the contracted carriage temperature of [Set Temp]°C with zero transit alarm triggers.\n\n` +
      `Proximate Cause: Because reefer equipment operated without mechanical failure or transit temperature abuse, the damage observed cannot be attributed to carrier refrigeration breakdown. ` +
      `The proximate cause of loss is attributable to pre-harvest latent fungal spore load (Botrytis cinerea) and natural senescence, aggravated by extended voyage transit.\n\n` +
      `As an act to mitigate the loss, we advised the consignees to sell the cargo as soon as possible to avoid further damages to Grape fruits.`
    );
  }

  // Condition 3: no_recorder_data
  const cRef = containerList.length > 1 ? `the subject containers` : `the subject container`;
  const serialSlot = containerList.length > 1 ? `(Serial Nos. [Serial Nos.])` : `(Serial No. [Serial No.])`;
  return (
    `According to the Bill of Lading, the requested temperature for this shipment of fresh Grapes was [Set Temp]°C. ` +
    `During our investigation, the Consignees informed us that they were unable to download the data from the temperature recorder ${serialSlot} ` +
    `installed inside ${cRef}. Consequently, we are unable to comment on any potential temperature anomalies that may have occurred during transit.\n\n` +
    `Based on our physical survey findings, we are of the opinion that the fresh Grapes likely sustained decay, berry softening, and stem dehydration ` +
    `due to temperature variations occurring during transit and/or pre-shipment stages, though the exact onset cannot be definitively fixed without recorder logs.`
  );
}

/**
 * Builds Paragraph 3 Cause of Loss for Plum (Report M-160).
 */
export function buildPlumCauseOfLoss(clauseContext: ClauseContext, condition: CauseCondition = 'carrier_breach'): string {
  const vals = clauseContext.values || {};
  const containerList: string[] = (vals as any).container_nos || (vals.container_no ? [vals.container_no] : []);

  if (condition === 'carrier_breach') {
    // Authentic M-160 wording
    return (
      `CAUSE OF DAMAGE & LIABILITY ASSESSMENT:\n\n` +
      `Carriage Instructions: As per the governing Bill of Lading [Bill of Lading No.], the carrier was instructed to carry this consignment of Fresh Plums strictly at [Set Temp]°C with fresh air exchange set at 15 m³/hr throughout the voyage.\n\n` +
      `• Temperature Breach: Reefer datalogger records confirm that the carrier failed to maintain the required carriage temperature, showing average recorded temperatures of [Avg Temp]°C. This substantial and continuous deviation proves the cargo suffered prolonged temperature abuse while in the carrier's custody.\n\n` +
      `• Biological Effect: Exposure to these elevated temperatures accelerated the ripening process, caused internal breakdown with deep brown to amber flesh discoloration, dry/mealy pulp, early alcoholic fermentation notes, and rapid fungal breakdown, directly resulting in the rotting observed during destuffing.\n\n` +
      `• Conclusion on Liability: The primary cause of loss is transit temperature abuse resulting directly from the carrier's failure to maintain the contracted [Set Temp]°C setting, rendering the entire consignment a total loss and unfit for human consumption.`
    );
  }

  if (condition === 'cold_chain_complied') {
    const cRef = containerList.length > 1
      ? `Reefer containers ${containerList.join(' & ')}`
      : (containerList.length === 1 ? `Reefer container ${containerList[0]}` : 'Reefer container [Container No.]');
    return (
      `Findings & Assessment:\n\n` +
      `Refrigeration Integrity: ${cRef} maintained continuous cold-chain compliance throughout transit from [Port of Loading] to [Port of Discharge]. ` +
      `Data logger records confirm that the reefer machinery operated without failure or transit temperature breach, maintaining an average of [Avg Temp]°C against the contracted [Set Temp]°C setpoint.\n\n` +
      `Proximate Cause: Transit temperature abuse is ruled out. The internal breakdown, flesh browning, and senescence observed across the plum fruits are attributable to inherent vice, over-maturity at harvest, or latent physiological breakdown.\n\n` +
      `Consignees were advised to sort and expedite sale of salvageable units to mitigate further loss.`
    );
  }

  // Condition 3: no_recorder_data
  const cRef = containerList.length > 1 ? `the subject containers` : `the subject container`;
  const serialSlot = containerList.length > 1 ? `(Serial Nos. [Serial Nos.])` : `(Serial No. [Serial No.])`;
  return (
    `According to the Bill of Lading, the requested temperature for this shipment of fresh Plums was [Set Temp]°C. ` +
    `During our investigation, the Consignees informed us that they were unable to download the data from the temperature recorder ${serialSlot} ` +
    `installed inside ${cRef}. Consequently, we are unable to comment on any potential temperature anomalies that may have occurred during transit.\n\n` +
    `Based on our physical survey findings and inspection of the cargo, we are of the opinion that the fresh Plums sustained internal breakdown, flesh browning, ` +
    `softening, and rot due to temperature variations occurring during transit and/or pre-shipment stages. ` +
    `However, the precise stage at which the deterioration commenced cannot be definitively established due to the unavailability of the temperature data log.`
  );
}

/**
 * Dispatches Paragraph 3 Cause of Loss generation to the appropriate fruit builder.
 */
export function buildParagraph3CauseOfLoss(clauseContext: ClauseContext, condition?: CauseCondition): string {
  const commodity = (clauseContext.commodity || '').toLowerCase();
  const cond = condition || detectCauseCondition(clauseContext);
  if (commodity.includes('pear')) {
    return buildPearCauseOfLoss(clauseContext, cond);
  }
  if (commodity.includes('mandarin')) {
    return buildMandarinCauseOfLoss(clauseContext, cond);
  }
  if (commodity.includes('grape')) {
    return buildGrapesCauseOfLoss(clauseContext, cond);
  }
  if (commodity.includes('plum')) {
    return buildPlumCauseOfLoss(clauseContext, cond);
  }
  return buildAppleCauseOfLoss(clauseContext, cond);
}

/**
 * Fills any known variables into Paragraph 3 Cause of Loss placeholders.
 */
export function fillCauseOfLossBlanks(text: string, clauseContext: ClauseContext): string {
  let updated = text;
  const vals = clauseContext.values || {};

  // Commodity / Fruit name
  const commodity = (clauseContext.commodity || 'Fruit').trim();
  const capCommodity = commodity.charAt(0).toUpperCase() + commodity.slice(1).toLowerCase();
  if (updated.includes('[Fruit]')) {
    updated = updated.split('[Fruit]').join(capCommodity);
  }

  // Bill of Lading No.
  const blNo = vals.bill_of_lading_no || vals.bl_no || vals.transport_doc;
  if (blNo) {
    if (updated.includes('[Bill of Lading No.]')) {
      updated = updated.split('[Bill of Lading No.]').join(`(${blNo})`);
    }
  } else {
    updated = updated.split('[Bill of Lading No.]').join('');
  }

  // Set Temp
  const setTemp = vals.set_temp || (vals as any).requested_temp;
  if (setTemp !== undefined && setTemp !== null && setTemp !== '') {
    const setStr = String(setTemp).trim();
    if (updated.includes('[Set Temp]°C')) {
      updated = updated.split('[Set Temp]°C').join(`${setStr}°C`);
    }
    if (updated.includes('[Set Temp]')) {
      updated = updated.split('[Set Temp]').join(setStr);
    }
  }

  // Avg Temp
  if (vals.avg_temp) {
    if (updated.includes('[Avg Temp]°C')) {
      updated = updated.split('[Avg Temp]°C').join(`${vals.avg_temp}°C`);
    }
    if (updated.includes('[Avg Temp]')) {
      updated = updated.split('[Avg Temp]').join(vals.avg_temp);
    }
  }

  // Min Temp
  if (vals.min_temp) {
    if (updated.includes('[Min Temp]°C')) {
      updated = updated.split('[Min Temp]°C').join(`${vals.min_temp}°C`);
    }
    if (updated.includes('[Min Temp]')) {
      updated = updated.split('[Min Temp]').join(vals.min_temp);
    }
  }

  // Max Temp
  if (vals.max_temp) {
    if (updated.includes('[Max Temp]°C')) {
      updated = updated.split('[Max Temp]°C').join(`${vals.max_temp}°C`);
    }
    if (updated.includes('[Max Temp]')) {
      updated = updated.split('[Max Temp]').join(vals.max_temp);
    }
  }

  // MKT
  if (vals.mkt_c) {
    if (updated.includes('[MKT]°C')) {
      updated = updated.split('[MKT]°C').join(`${vals.mkt_c}°C`);
    }
    if (updated.includes('[MKT]')) {
      updated = updated.split('[MKT]').join(vals.mkt_c);
    }
  }

  // Trip length
  if (vals.trip_length && updated.includes('[Trip Length]')) {
    updated = updated.split('[Trip Length]').join(vals.trip_length);
  }

  // Container numbers
  const containerList: string[] = (vals as any).container_nos || (vals.container_no ? [vals.container_no] : []);
  if (containerList.length === 1) {
    if (updated.includes('[Container No.]')) {
      updated = updated.split('[Container No.]').join(containerList[0]);
    }
    if (updated.includes('[Container Nos.]')) {
      updated = updated.split('[Container Nos.]').join(containerList[0]);
    }
  } else if (containerList.length > 1) {
    if (updated.includes('Reefer container [Container No.]')) {
      updated = updated.split('Reefer container [Container No.]').join(`Reefer containers ${containerList.join(' & ')}`);
    }
    if (updated.includes('[Container Nos.]')) {
      updated = updated.split('[Container Nos.]').join(containerList.join(' & '));
    }
    if (updated.includes('[Container No.]')) {
      updated = updated.split('[Container No.]').join(containerList.join(' & '));
    }
  }

  // Ports
  const pol = vals.port_of_loading || vals.origin_port;
  if (pol) {
    if (updated.includes('[Port of Loading]')) {
      updated = updated.split('[Port of Loading]').join(pol);
    }
    if (updated.includes('[Origin Port]')) {
      updated = updated.split('[Origin Port]').join(pol);
    }
  }

  const pod = vals.port_of_discharge || vals.destination_port;
  if (pod) {
    if (updated.includes('[Port of Discharge]')) {
      updated = updated.split('[Port of Discharge]').join(pod);
    }
    if (updated.includes('[Destination Port]')) {
      updated = updated.split('[Destination Port]').join(pod);
    }
  }

  // Vessel
  if (vals.vessel) {
    if (updated.includes('[Vessel Name & Voyage No.]')) {
      updated = updated.split('[Vessel Name & Voyage No.]').join(vals.vessel);
    }
    if (updated.includes('[Vessel]')) {
      updated = updated.split('[Vessel]').join(vals.vessel);
    }
  }

  // Serial No. / IMEI No.
  const serial = vals.serial_no || vals.device_id || vals.imei_no;
  if (serial) {
    if (updated.includes('[Serial No.]')) {
      updated = updated.split('[Serial No.]').join(serial);
    }
    if (updated.includes('[Serial Nos.]')) {
      updated = updated.split('[Serial Nos.]').join(serial);
    }
    if (updated.includes('[IMEI No.]')) {
      updated = updated.split('[IMEI No.]').join(serial);
    }
    if (updated.includes('[IMEI Nos.]')) {
      updated = updated.split('[IMEI Nos.]').join(serial);
    }
  }

  return updated;
}




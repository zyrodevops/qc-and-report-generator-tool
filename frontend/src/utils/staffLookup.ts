import staffDataRaw from '../data/staff_and_surveyors.json';

export interface Attendee {
  name: string;
  designation: string;
  representing: string;
  line?: string;
}

export interface StaffSurveyorData {
  consignees: { company: string; name: string; designation: string; representing: string }[];
  shipping_lines: { company?: string; name: string; designation: string; representing: string; line: string }[];
  shippers: { name: string; designation: string; representing: string }[];
  cargo_insurers: { name: string; designation: string; representing: string }[];
  mca_surveyors: { name: string; designation: string; representing: string }[];
}

export const staffData: StaffSurveyorData = staffDataRaw as StaffSurveyorData;

function cleanStr(s: string): string {
  let res = (s || '').toLowerCase();
  // Remove parenthetical notes first
  res = res.replace(/\((?:consignees?|consignee's|consignee's customers|consignees end buyer \/ vendor)\)/gi, ' ');
  // Remove entity and stop words as complete words
  res = res.replace(/\b(?:pvt|ltd|limited|llp|co|company|and|m\/s)\b/gi, ' ');
  // Remove punctuation
  res = res.replace(/[-.,'"&]/g, ' ');
  return res.split(/\s+/).filter(Boolean).join(' ');
}

export function lookupConsigneeStaff(consigneeName: string): Attendee[] {
  if (!consigneeName || consigneeName.startsWith('[')) return [];
  const cleanedInput = cleanStr(consigneeName);
  if (!cleanedInput) return [];

  const consignees = staffData.consignees || [];

  // 1. Exact cleaned match
  const exact = consignees.filter((c) => cleanStr(c.company) === cleanedInput);
  if (exact.length > 0) return dedup(exact);

  // 2. Phrase matching (either input contains company or company contains input as whole word)
  const phraseMatches: any[] = [];
  for (const c of consignees) {
    const cleanedComp = cleanStr(c.company);
    if (!cleanedComp) continue;
    const regex1 = new RegExp(`\\b${cleanedComp}\\b`, 'i');
    const regex2 = new RegExp(`\\b${cleanedInput}\\b`, 'i');
    if (regex1.test(cleanedInput) || regex2.test(cleanedComp)) {
      phraseMatches.push(c);
    }
  }
  if (phraseMatches.length > 0) return dedup(phraseMatches);

  // 3. Significant token match
  const inputTokens = new Set(cleanedInput.split(' ').filter((t) => t.length > 1));
  const tokenMatches: any[] = [];
  for (const c of consignees) {
    const cleanedComp = cleanStr(c.company);
    const compTokens = new Set(cleanedComp.split(' ').filter((t) => t.length > 1));
    const intersection = [...compTokens].filter((t) => inputTokens.has(t));
    if (compTokens.size > 0 && intersection.length === compTokens.size) {
      tokenMatches.push(c);
    } else if (intersection.length >= 2) {
      tokenMatches.push(c);
    }
  }

  return dedup(tokenMatches);
}

function dedup(list: any[]): Attendee[] {
  const seen = new Set<string>();
  const out: Attendee[] = [];
  for (const item of list) {
    const key = `${item.name}|${item.representing}`;
    if (!seen.has(key)) {
      seen.add(key);
      out.push({
        name: item.name,
        designation: item.designation,
        representing: item.representing,
      });
    }
  }
  return out;
}

export function getDefaultAttendance(consigneeName = ''): Attendee[] {
  const list: Attendee[] = [];
  const matched = lookupConsigneeStaff(consigneeName);
  for (const m of matched) {
    list.push(m);
  }
  // Default MCA surveyor
  list.push({
    name: 'Mr. Baburao Bhosale',
    designation: 'Surveyor',
    representing: 'Marine Cargo Agencies Pvt.Ltd (On behalf of Consignees)',
  });
  return list;
}

export function suggestShippingLineSurveyors(vesselName: string): Attendee[] {
  if (!vesselName) return [];
  const v = vesselName.toLowerCase();
  const res: Attendee[] = [];
  if (v.includes('wan hai')) {
    const found = staffData.shipping_lines.filter((s) => s.line === 'Wan Hai');
    res.push(...found);
  } else if (v.includes('oocl')) {
    const found = staffData.shipping_lines.filter((s) => s.line === 'OOCL');
    res.push(...found);
  }
  return res;
}

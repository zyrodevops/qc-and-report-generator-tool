import { getStaffData } from './referenceData';

export type { StaffSurveyorData } from './referenceData';

export interface Attendee {
  name: string;
  designation: string;
  representing: string;
  line?: string;
}

/** The firm's own surveyor added to every attendance table (first on the list). */
export function defaultSurveyor(): Attendee | null {
  const s = getStaffData().mca_surveyors[0];
  return s ? { name: s.name, designation: s.designation, representing: s.representing } : null;
}

/** A row for the firm's own surveyor (kept when the consignee's staff are swapped). */
export function isMcaAttendee(row: { name?: string; representing?: string }): boolean {
  if ((row.representing || '').toLowerCase().includes('marine cargo agencies')) return true;
  const name = bareName(row.name);
  return !!name && getStaffData().mca_surveyors.some((s) => bareName(s.name) === name);
}

/** "Mr. A. Kumar " → "a. kumar", so a name typed with or without the title still matches. */
function bareName(name?: string): string {
  return (name || '').trim().toLowerCase().replace(/^(mr|mrs|ms|dr|capt)\.?\s+/, '');
}

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

  const consignees = getStaffData().consignees || [];

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
  const surveyor = defaultSurveyor();
  if (surveyor) list.push(surveyor);
  return list;
}

export function suggestShippingLineSurveyors(vesselName: string): Attendee[] {
  if (!vesselName) return [];
  const v = vesselName.toLowerCase();
  const res: Attendee[] = [];
  const lines = getStaffData().shipping_lines;
  if (v.includes('wan hai')) {
    const found = lines.filter((s) => s.line === 'Wan Hai');
    res.push(...found);
  } else if (v.includes('oocl')) {
    const found = lines.filter((s) => s.line === 'OOCL');
    res.push(...found);
  }
  return res;
}

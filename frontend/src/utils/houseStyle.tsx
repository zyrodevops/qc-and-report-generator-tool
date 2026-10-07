/**
 * The client's report look in the A4 preview — the same values and rules as
 * the Word file (backend app/render/house_style.py and app/render/docx/house.py).
 *
 * Survey reports (fruit and general cargo) take it; QC reports keep their own.
 * Text the tool writes can mark words for the printed report:
 *   **words**  bold
 *   __words__  underlined
 *   ## line    a sub-heading (bold, underlined, dark blue) on a line of its own
 */
import React, { createContext, useContext } from 'react';
import { getStoredToken } from '../api/client';

export const HOUSE_BLUE = '#002060';
export const COMPANY = 'MARINE CARGO AGENCIES PRIVATE LIMITED';
export const PHOTOS_HEADING = 'SURVEY PHOTOGRAPHS';
export const DISCLAIMER_HEADING = 'DISCLAIMER & RESERVATION OF RIGHTS:';
export const DISCLAIMER =
  'This report reflects an impartial professional assessment based strictly upon physical observations, ' +
  'empirical sampling, and documents made available up to the time of survey. It is issued in good faith ' +
  'and strictly Without Prejudice to the substantive legal rights, remedies, liabilities, and defences of ' +
  'any interested parties under the applicable contract of carriage, bill of lading, air waybill, ' +
  'international conventions (such as Hague-Visby, Hamburg, Montreal, or Warsaw Rules), or governing ' +
  'insurance policies. The surveyor expressly reserves the right to amend, alter, or supplement the ' +
  'findings and conclusions herein should supplementary facts, electronic datalogger downloads, transit ' +
  'records, or further material documentation subsequently becomes available.';
export const ISSUED = '“ISSUED WITHOUT PREJUDICE”';
export const PLACE = 'Mumbai, India.';
export const LICENCE_PLACEHOLDER = '[License No.]';
export const SURVEYOR_PLACEHOLDER = '[Surveyor Name]';
export const SIGNATURE_LABEL = 'Signature of Reporting Surveyor';
export const END_MARK = 'ØØØ';

/** True inside the A4 pages of a survey report. */
export const HouseStyleContext = createContext<boolean>(false);
export const useHouseStyle = () => useContext(HouseStyleContext);

export function isSurveyReport(metadata: any, report?: any): boolean {
  const fam = String(metadata?.family || report?.family || '').toUpperCase();
  return fam ? fam === 'SURVEY_REPORT' : true;
}

/** FINAL SURVEY REPORT NO. M-109-2026 — the number given when the report was made. */
export function reportTitle(metadata: any, reportNumber?: string): string {
  const stage = String(metadata?.state || '').toUpperCase() === 'PRELIMINARY' ? 'PRELIMINARY' : 'FINAL';
  const num = String(metadata?.number || reportNumber || '').trim();
  return num ? `${stage} SURVEY REPORT NO. ${num}` : `${stage} SURVEY REPORT`;
}

/** 'PARAGRAPH 1: APPLICATION:'; the note is 'Note:'. */
export function headingText(section: string): string {
  const t = String(section || '').split(/\s+/).filter(Boolean).join(' ');
  if (!t) return '';
  if (t.replace(/:+$/, '').toUpperCase() === 'NOTE') return 'Note:';
  return /[:)]$/.test(t) ? t : `${t}:`;
}

export function bannerUrl(): string {
  const token = getStoredToken();
  return `/api/reference-data/banner.jpg${token ? `?auth_token=${encodeURIComponent(token)}` : ''}`;
}

// ---------------------------------------------------------------------------
// Marks
// ---------------------------------------------------------------------------

export type Run = { text: string; bold: boolean; under: boolean };

export function runs(text: string): Run[] {
  const out: Run[] = [];
  let bold = false;
  let under = false;
  for (const part of String(text || '').split(/(\*\*|__)/)) {
    if (part === '**') bold = !bold;
    else if (part === '__') under = !under;
    else if (part) out.push({ text: part, bold, under });
  }
  return out;
}

/** The text without its marks. */
export function plain(text: string): string {
  return String(text || '')
    .replace(/\*\*|__/g, '')
    .split('\n')
    .map((l) => l.replace(/^\s*##\s+/, ''))
    .join('\n');
}

type Part = { kind: 'p' | 'ul' | 'ol' | 'h'; lines: string[] };

const BULLET = /^\s*(?:[•●▪➢]|-(?=\s))\s*/;
const NUMBERED = /^\s*\d{1,2}\)\s+/;
const SUBHEADING = /^\s*##\s+(.*\S)\s*$/;

/** Same split as the server's split_narrative(rich=True). */
export function splitNarrative(text: string): Part[] {
  const out: Part[] = [];
  for (const block of String(text || '').split(/\n[ \t]*\n/)) {
    let para: string[] = [];
    let items: string[] = [];
    let kind: 'ul' | 'ol' = 'ul';
    const flushPara = () => {
      if (para.length) out.push({ kind: 'p', lines: para });
      para = [];
    };
    const flushItems = () => {
      if (items.length) out.push({ kind, lines: items });
      items = [];
    };
    for (const line of block.split('\n')) {
      if (!line.trim()) continue;
      const sub = line.match(SUBHEADING);
      if (sub) {
        flushPara();
        flushItems();
        out.push({ kind: 'h', lines: [sub[1]] });
      } else if (BULLET.test(line) || NUMBERED.test(line)) {
        const lk = NUMBERED.test(line) ? 'ol' : 'ul';
        flushPara();
        if (items.length && lk !== kind) flushItems();
        kind = lk;
        items.push(lk === 'ol' ? line.trim() : line.replace(BULLET, '').trim());
      } else {
        flushItems();
        para.push(line.trim());
      }
    }
    flushPara();
    flushItems();
  }
  return out;
}

// ---------------------------------------------------------------------------
// The client's bold / underline rules, applied when the report is shown —
// the same rules as the Word file (house_style.auto_marks). The 5 fruits only;
// a line that already carries marks is left as it is.
// ---------------------------------------------------------------------------

export const CURATED_FRUITS = ['apple', 'pear', 'mandarin', 'mandarins', 'grape', 'grapes', 'plum', 'plums'];

const SUBHEAD_LINES =
  /^\s*(?:(?:THE\s+)?CONDITION FOUND OF\b.*:|CAUSE OF LOSS:?|CAUSE OF DAMAGE & LIABILITY ASSESSMENT:?|Findings & Assessment:|Refrigeration Integrity:|Proximate Cause:|Pulp condition after cutting & the Taste:|Internal Pulp Condition.*:)\s*$/i;
const RUN_IN_SUBHEAD = /^(\s*)(Refrigeration Integrity:|Proximate Cause:|Pulp condition after cutting & the Taste:)(\s+\S.*)$/i;
const LEAD_INS =
  /^(\s*)((?:The \w+ fruits were cut, and the following pulp conditions were observed|Based on our physical survey findings and taking the above into consideration, we conclude as follows|Additional contributing factors observed during the inspection include))(\s*:\s*)$/i;
const FACTORS_LEAD = /^\s*_*Additional contributing factors observed during the inspection include/i;
const PRESSURE_BULLET = /^(\s*(?:[•●▪➢]|-)\s*)(.+?\(\s*\d+\s*Count\s*\):)(\s+.*)$/i;
const PRESSURE_NUMBERED = /^(\s*\d{1,2}\)\s*)(.*?)(\(\s*\d+\s*Count\s*\):)(\s+.*)$/i;
const BULLET_LABEL = /^(\s*(?:[•●▪➢]|-)\s*)([A-Z][A-Za-z/&()' -]{1,45}?:)(\s+\S.*)$/;
const FACTOR_BULLET = /^(\s*(?:[•●▪➢]|-)\s*)(.+?)((?:,|\s+indicative\b|\s+likely\b|\s+such as\b|\.$).*)$/i;
const CARRIAGE = /^(\s*)(Carriage Instructions:)/i;
const SAMPLE = /(During our inspection, )(\S+ boxes out of the \S+ boxes)/g;
const OPINION = /(We are of the opinion that the fresh )(.+?pre-shipment stages)(?=[.,])/g;
const ANNEXURE = /(?<![*\w])(Annexure\s+[A-Z]\d*(?:\s*&\s*[A-Z]?\d+)?)(?![\w*])/g;
const SEE_PHOTOS = /(?<!\*)(\(See Photos? [^)]+\))/g;

export function autoMarks(text: string, fruit?: string): string {
  const f = String(fruit || '').trim().toLowerCase();
  if (!text || !CURATED_FRUITS.includes(f)) return text || '';
  const pear = f === 'pear';
  const out: string[] = [];
  let inFactors = false;
  for (let line of text.split('\n')) {
    const stripped = line.trim();
    if (!stripped) {
      out.push(line);
      continue;
    }
    const isBullet = '•●▪➢'.includes(stripped[0]) || stripped.startsWith('- ');
    const factorsHere = inFactors;
    if (!isBullet) inFactors = FACTORS_LEAD.test(line);
    if (line.includes('**') || line.includes('__') || SUBHEADING.test(line)) {
      out.push(line);
      continue;
    }
    let m: RegExpMatchArray | null;
    if (SUBHEAD_LINES.test(line)) line = `## ${stripped}`;
    else if ((m = line.match(RUN_IN_SUBHEAD))) line = `${m[1]}**__${m[2]}__**${m[3]}`;
    else if ((m = line.match(LEAD_INS))) line = `${m[1]}__${m[2]}__${m[3].trimEnd()}`;
    else if ((m = line.match(PRESSURE_NUMBERED))) line = pear ? `${m[1]}${m[2]}**${m[3]}**${m[4]}` : `${m[1]}**${m[2]}${m[3]}**${m[4]}`;
    else if (isBullet && (m = line.match(PRESSURE_BULLET))) line = `${m[1]}**${m[2]}**${m[3]}`;
    else if (isBullet && factorsHere && (m = line.match(FACTOR_BULLET))) line = `${m[1]}**${m[2]}**${m[3]}`;
    else if (isBullet && (m = line.match(BULLET_LABEL)) && m[2].split(/\s+/).filter(Boolean).length <= 5) line = `${m[1]}**${m[2]}**${m[3]}`;
    else if ((m = line.match(CARRIAGE))) line = `${m[1]}**${m[2]}**${line.slice(m[0].length)}`;
    line = line
      .replace(SAMPLE, '$1**$2**')
      .replace(OPINION, '$1**$2**')
      .replace(ANNEXURE, '**$1**')
      .replace(SEE_PHOTOS, '**$1**');
    out.push(line);
  }
  return out.join('\n');
}

export const Marked: React.FC<{ text: string }> = ({ text }) => (
  <>
    {runs(text).map((r, i) => {
      let el: React.ReactNode = r.text;
      if (r.under) el = <u>{el}</u>;
      if (r.bold) el = <b>{el}</b>;
      return <React.Fragment key={i}>{el}</React.Fragment>;
    })}
  </>
);

/** One paragraph, list or sub-heading, as printed. */
const PartView: React.FC<{ part: Part }> = ({ part }) => {
  if (part.kind === 'h') return <p className="mca-heading">{part.lines[0]}</p>;
  if (part.kind === 'ul' || part.kind === 'ol') {
    return (
      <div className="mca-list">
        {part.lines.map((item, j) => {
          const [lead, rest] = part.kind === 'ol' ? [item.split(' ')[0], item.slice(item.indexOf(' ') + 1)] : ['\u2022', item];
          return (
            <div key={j} className="mca-li">
              <span className="mca-li-mark">{lead}</span>
              <span className="mca-li-text">
                <Marked text={rest} />
              </span>
            </div>
          );
        })}
      </div>
    );
  }
  return (
    <p className="mca-p">
      {part.lines.map((l, j) => (
        <React.Fragment key={j}>
          {j > 0 && <br />}
          <Marked text={l} />
        </React.Fragment>
      ))}
    </p>
  );
};

/** A section's text as the report prints it: paragraphs, bullets, numbered lines, sub-headings. */
export const RichText: React.FC<{ text: string; fruit?: string }> = ({ text, fruit }) => (
  <>
    {splitNarrative(autoMarks(text, fruit)).map((part, i) => (
      <PartView key={i} part={part} />
    ))}
  </>
);

// ---------------------------------------------------------------------------
// A section as printed pieces, so the A4 preview can break pages between
// paragraphs the way Word does.
// ---------------------------------------------------------------------------

export type Piece =
  | { kind: 'heading' }
  | { kind: 'pre'; part: number }
  | { kind: 'rec'; index: number }
  | { kind: 'text'; part: number }
  | { kind: 'att' };

export function narrativePieces(
  block: any,
  fruit: string | undefined,
  opts: { heading: boolean; recorders: number; attendance: boolean }
): Piece[] {
  const pieces: Piece[] = [];
  if (opts.heading) pieces.push({ kind: 'heading' });
  splitNarrative(autoMarks(String(block?.preamble || ''), fruit)).forEach((_, i) => pieces.push({ kind: 'pre', part: i }));
  for (let i = 0; i < opts.recorders; i++) pieces.push({ kind: 'rec', index: i });
  splitNarrative(autoMarks(String(block?.additional_text || ''), fruit)).forEach((_, i) => pieces.push({ kind: 'text', part: i }));
  if (opts.attendance) pieces.push({ kind: 'att' });
  return pieces;
}

/** One paragraph / list / sub-heading of a section's text (see RichText). */
export const RichPart: React.FC<{ text: string; fruit?: string; part: number }> = ({ text, fruit, part }) => {
  const p = splitNarrative(autoMarks(text, fruit))[part];
  return p ? <PartView part={p} /> : null;
};

// ---------------------------------------------------------------------------
// The closing
// ---------------------------------------------------------------------------

const ordinal = (d: number) => (d % 100 >= 11 && d % 100 <= 13 ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' } as any)[d % 10] || 'th');

/** The report date: set on the closing, else the 'Dated:' line of an older report, else today. */
export function closingDate(block: any): Date {
  const raw = String(block?.dated || '').trim();
  const iso = raw.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (iso) return new Date(Number(iso[1]), Number(iso[2]) - 1, Number(iso[3]));
  const old = String(block?.content || '').match(/Dated:\s*(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})/);
  if (old) {
    const d = new Date(`${old[1]} ${old[2]} ${old[3]}`);
    if (!Number.isNaN(d.getTime())) return d;
  }
  return new Date();
}

export function isoDate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/** ['28', 'th', ' September 2026.'] — the suffix is printed raised. */
export function datedParts(block: any): [string, string, string] {
  const d = closingDate(block);
  const month = d.toLocaleString('en-GB', { month: 'long' });
  return [String(d.getDate()), ordinal(d.getDate()), ` ${month} ${d.getFullYear()}.`];
}

export function licenceLine(licence?: string): string {
  const lic = String(licence || '').trim().replace(/\.$/, '') || LICENCE_PLACEHOLDER;
  return `(IRDA Surveyor License No.): ${lic}.`;
}

/** The firm's surveyor from the attendance table, as signed: 'Baburao Bhosale'. */
export function reportingSurveyor(blocks: any[], fallback?: string): string {
  const clean = (n: string) => n.replace(/^(?:mr|mrs|ms|dr|capt)\.?\s+/i, '').replace(/\s*&\s*team\s*$/i, '').trim();
  for (const b of blocks || []) {
    for (const row of b?.attendance || []) {
      const name = String(row?.name || '').split(/\s+/).filter(Boolean).join(' ');
      if (name && /marine cargo agencies/i.test(String(row?.representing || ''))) return clean(name) || SURVEYOR_PLACEHOLDER;
    }
  }
  return fallback ? clean(fallback) : SURVEYOR_PLACEHOLDER;
}

export function isClosing(block: any, metadata: any): boolean {
  return (
    block?.type === 'fixed_text' &&
    (block?.kind === 'closing' || block?.id === 'b_closure') &&
    metadata?.report_kind !== 'general_cargo'
  );
}

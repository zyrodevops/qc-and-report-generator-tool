import React from 'react';
import {
  COMPANY,
  DISCLAIMER,
  DISCLAIMER_HEADING,
  END_MARK,
  ISSUED,
  PLACE,
  SIGNATURE_LABEL,
  closingDate,
  datedParts,
  isClosing,
  isoDate,
  licenceLine,
  reportingSurveyor,
  RichText,
} from '../../../utils/houseStyle';
import { getLicenceNo, getStaffData, useReferenceData } from '../../../utils/referenceData';

export interface FixedTextBlockProps {
  block: any;
  metadata?: any;
  /** All blocks of the report, for the reporting surveyor's name (attendance table). */
  blocks?: any[];
}

/**
 * The closing text, exactly as the Word file prints it.
 *
 * A fruit survey report closes as the client's do (house_style.py): the
 * disclaimer, "ISSUED WITHOUT PREJUDICE" with the date, place and licence
 * line, two signature spaces — the stamps and signatures go on by hand — and
 * ØØØ. Any other report prints the block's own lines and nothing else.
 */
export const FixedTextBlock: React.FC<FixedTextBlockProps> = ({ block, metadata, blocks }) => {
  useReferenceData();
  if (isClosing(block, metadata)) {
    const [day, suffix, rest] = datedParts(block);
    const firstMca = getStaffData().mca_surveyors[0]?.name;
    return (
      <div className="closing-block" data-testid="closing-block" style={{ breakInside: 'avoid' }}>
        <p className="mca-small" style={{ fontWeight: 700, fontStyle: 'italic', textDecoration: 'underline', margin: '6pt 0 8pt' }}>
          {DISCLAIMER_HEADING}
        </p>
        <p className="mca-small" style={{ fontStyle: 'italic', textAlign: 'justify', margin: '0 0 12pt' }}>
          {DISCLAIMER}
        </p>
        <div style={{ fontWeight: 700, marginBottom: '18pt' }}>
          <div>{ISSUED}</div>
          <div>
            Dated: {day}
            <sup>{suffix}</sup>
            {rest}
          </div>
          <div>Place: {String(block?.place || '').trim() || PLACE}</div>
          <div>{licenceLine(getLicenceNo())}</div>
        </div>
        <div className="flex justify-between">
          <div style={{ width: '6cm', height: '3.2cm' }} data-testid="signature-space-left" />
          <div className="text-right" style={{ flex: 1 }}>
            <div>{SIGNATURE_LABEL}</div>
            <div style={{ height: '2.6cm' }} data-testid="signature-space-right" />
            <div>{reportingSurveyor(blocks || [], firstMca)}</div>
            <div style={{ fontWeight: 700, fontSize: '10pt' }}>{COMPANY}</div>
          </div>
        </div>
        <p style={{ textAlign: 'center', fontWeight: 700, color: '#002060', margin: '2pt 0 0' }}>{END_MARK}</p>
      </div>
    );
  }

  const content = String(block?.content || '');
  if (!content.trim()) return null;
  return (
    <div className="fixed-text-block my-4 pt-2 text-[10pt] leading-relaxed text-slate-800">
      {content.split(/\n\s*\n/).map((para, i) => (
        <p key={i} className="whitespace-pre-line mb-2">
          {para}
        </p>
      ))}
    </div>
  );
};

/**
 * Form editor: the closing's date and place. The disclaimer, licence line and
 * signature spaces are fixed and print as in the client's reports.
 */
export const ClosingEditor: React.FC<{ block: any; onChange: (b: any) => void }> = ({ block, onChange }) => {
  const dated = isoDate(closingDate(block));
  return (
    <div className="bg-gray-50 rounded-xl border border-gray-200 p-5 text-xs text-gray-700 space-y-3" data-testid="closing-editor">
      <div className="font-bold text-gray-800 uppercase">Closing: Issued without prejudice</div>
      <div className="flex flex-wrap gap-4 items-end">
        <label className="flex flex-col gap-1">
          <span className="font-semibold">Dated</span>
          <input
            type="date"
            value={dated}
            onChange={(e) => e.target.value && onChange({ ...block, dated: e.target.value })}
            className="border border-gray-300 rounded px-2 py-1"
            data-testid="closing-dated"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="font-semibold">Place</span>
          <input
            type="text"
            value={block?.place ?? PLACE}
            onChange={(e) => onChange({ ...block, place: e.target.value })}
            className="border border-gray-300 rounded px-2 py-1 w-56"
          />
        </label>
      </div>
      <p className="text-gray-500">
        The disclaimer, the licence line and the two signature spaces print as in the client's reports; the stamps and
        signatures are put on by hand.
      </p>
    </div>
  );
};

export { RichText };

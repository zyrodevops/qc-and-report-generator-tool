import React from 'react';
import { AttendanceBlock } from './AttendanceBlock';
import { GridTable, unitSegments, unitTable } from '../../../utils/gcTables';
import { GridTableBlock } from './GridTableBlock';

/** Paragraphs split on blank lines, list items on "• ", as the Word file does. */
const Body: React.FC<{ text: string }> = ({ text }) => {
  if (!text.trim()) return null;
  return (
    <div className="text-[10pt] leading-relaxed space-y-1.5">
      {text.split(/\n\s*\n/).map((para, i) => {
        const lines = para.split('\n').filter((l) => l.trim());
        const bullets = lines.length > 0 && lines.every((l) => /^\s*[•\-–]\s+/.test(l));
        return bullets ? (
          <ul key={i} className="list-disc pl-5">
            {lines.map((l, j) => (
              <li key={j}>{l.replace(/^\s*[•\-–]\s+/, '')}</li>
            ))}
          </ul>
        ) : (
          <p key={i} className="whitespace-pre-line">{lines.join('\n')}</p>
        );
      })}
    </div>
  );
};

/**
 * One OUR SURVEY paragraph of a general cargo report, laid out as the Word
 * file: people who attended after its opening paragraph, its tables (damage,
 * tally, weighbridge) at their marks or after the text, and on the last
 * paragraph the WEIGHT FINAL SUMMARY.
 */
export const SurveyUnitBlock: React.FC<{ block: any; summary?: GridTable | null }> = ({ block, summary }) => {
  const people = (block?.attendance || []).filter((r: any) =>
    ['name', 'designation', 'representing'].some((k) => String(r?.[k] ?? '').trim()),
  );
  let firstText = true;
  return (
    <div className="survey-unit-block my-2">
      <h2 className="text-[12px] font-bold text-[#00387A] uppercase tracking-wider border-b border-slate-300 pb-1 mb-2">
        {block?._heading || 'OUR SURVEY:'}
      </h2>
      {unitSegments(String(block?.additional_text || '')).map((seg, i) => {
        if (seg.kind === 'table') {
          return <GridTableBlock key={i} table={unitTable(block, seg.value)} testId={`${seg.value}-table`} />;
        }
        const text = seg.value;
        const isFirst = firstText;
        firstText = false;
        if (!isFirst || !people.length) return <Body key={i} text={text} />;
        const cut = text.indexOf('\n\n');
        return (
          <React.Fragment key={i}>
            <Body text={cut >= 0 ? text.slice(0, cut) : text} />
            <AttendanceBlock
              block={{ id: `${block.id}_att`, type: 'attendance', rows: people, ...({ title: '', intro: block.attendance_intro ?? 'The following persons attended the survey:' } as any) }}
              editable={false}
            />
            <Body text={cut >= 0 ? text.slice(cut + 2) : ''} />
          </React.Fragment>
        );
      })}
      <GridTableBlock table={summary || null} testId="weight-summary" />
    </div>
  );
};

export default SurveyUnitBlock;

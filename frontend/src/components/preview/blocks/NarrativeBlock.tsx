import React, { useRef, useLayoutEffect, useEffect } from 'react';
import { ClausePicker, WithBlanks, detectSectionFromHeading } from '../../clauses/ClausePicker';
import { NotesWriter } from '../../clauses/NotesWriter';
import { ColdStorageSelector } from '../../clauses/ColdStorageSelector';
import { ApplicationAttendance } from '../../clauses/ApplicationAttendance';
import { getDefaultAttendance, lookupConsigneeStaff } from '../../../utils/staffLookup';
import type { ClauseContext } from '../../../api/client';
import {
  BLANK_PATTERN,
  buildCircumstancesText,
  buildMandarinCircumstances,
  buildGrapesCircumstances,
  buildPlumCircumstances,
  fillCircumstancesBlanks,
  MANDARIN_NOTE_TEXT,
  buildAppleOurSurvey,
  buildPearOurSurvey,
  buildMandarinOurSurvey,
  buildGrapesOurSurvey,
  buildPlumOurSurvey,
  fillOurSurveyBlanks,
} from '../../../utils/clauseContext';

export interface NarrativeBlockProps {
  block: any;
  onChange?: (updatedBlock: any) => void;
  editable?: boolean;
  /** Fruit, container, measurements and counted defects, for the clause picker. */
  clauseContext?: ClauseContext;
  /** Shown instead of the section name (general cargo: the numbered heading). Never saved. */
  heading?: string;
  /** Which wording to offer, when the heading does not say (a general cargo survey paragraph). */
  clauseSection?: string;
  /** True when rendered in the Form Editor tab, false in A4 HTML Preview. */
  isFormEditor?: boolean;
}

export const NarrativeBlock: React.FC<NarrativeBlockProps> = ({
  block,
  onChange,
  editable = true,
  clauseContext,
  heading,
  clauseSection,
  isFormEditor = false,
}) => {
  const sectionTitle = heading || block?._heading || block?.section || 'ATTENDANCE & CIRCUMSTANCES';
  const text = block?.additional_text || '';
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  // useLayoutEffect fires synchronously after DOM mutation but before browser paint,
  // so the resize happens immediately even when text is set programmatically
  // (e.g. clause insertion), preventing overflow-hidden from clipping content.
  useLayoutEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.max(80, el.scrollHeight)}px`;
  }, [text, editable]);

  if (!text && !sectionTitle && !editable) return null;

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    if (!onChange) return;
    onChange({
      ...block,
      additional_text: e.target.value,
      surveyor_edited: true,
    });
  };

  const focusEnd = () =>
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        textareaRef.current.selectionStart = textareaRef.current.value.length;
        textareaRef.current.selectionEnd = textareaRef.current.value.length;
      }
    }, 50);

  // Topics added from the standard wording, and the exact text each added, so
  // that one can be taken out again. Kept on the block, so it survives a save.
  const addedTopics: Record<string, string> = block?.wording_added || {};

  /** Add a topic's text at the end: a new paragraph, or the next bullet of a list. */
  const handleAddTopic = (topic: string, topicText: string) => {
    if (!onChange) return;
    const current = text.replace(/\s+$/, '');
    const lastLine = current.split('\n').pop() || '';
    const joiner = !current ? '' : /^\s*•/.test(lastLine) && /^\s*•/.test(topicText) ? '\n' : '\n\n';
    onChange({
      ...block,
      additional_text: current + joiner + topicText,
      wording_added: { ...addedTopics, [topic]: topicText },
      surveyor_edited: true,
    });
    focusEnd();
  };

  /**
   * Take a topic's text back out. Only the exact text that was added is
   * removed; if the surveyor has since edited it, it cannot be found, and he
   * is told rather than having a guess at which words to delete.
   */
  const handleRemoveTopic = (topic: string) => {
    if (!onChange) return;
    const addedText = addedTopics[topic];
    const { [topic]: _gone, ...rest } = addedTopics;
    const at = addedText ? text.indexOf(addedText) : -1;
    if (at < 0) {
      const ok = window.confirm(
        'This text has been edited since it was added, so it cannot be taken out automatically. ' +
          'Delete it from the text box by hand.\n\nMark this topic as not added?',
      );
      if (ok) onChange({ ...block, wording_added: rest });
      return;
    }
    const next = (text.slice(0, at) + text.slice(at + addedText.length))
      .replace(/\n{3,}/g, '\n\n')
      .replace(/^\s+|\s+$/g, '');
    onChange({ ...block, additional_text: next, wording_added: rest, surveyor_edited: true });
  };

  const sectionSlug = clauseSection || detectSectionFromHeading(sectionTitle);
  const blanks = text.match(BLANK_PATTERN) || [];

  const commodityKey = (clauseContext?.commodity || '').toLowerCase();
  // Option cards hidden for curated fruits (apple, grapes, plum, pear, mandarin) per user instruction (kept preserved in code)
  const isCuratedFruit = ['apple', 'grapes', 'grape', 'plum', 'pear', 'mandarin'].includes(commodityKey);
  const hideClausePicker = sectionSlug === 'application' || isCuratedFruit;
  const isCircumstances = sectionSlug === 'circumstances_of_loss' || /circumstance/i.test(sectionTitle);

  const consigneeName = String(clauseContext?.values?.consignee || '');
  const vesselName = String(clauseContext?.values?.vessel || '');

  // Pre-populate Paragraph 1 Application section with standard cold storage template for all fruits if empty
  useEffect(() => {
    if (sectionSlug === 'application' && !text.trim() && onChange) {
      const defaultText =
        "Pursuant to the Consignee's request and subsequent appointment, we attended the Consignee's nominated cold storage facility, M/s [Cold Storage Name] ([Cold Storage Address]), on [Survey Date], to carry out an inspection of the subject consignment.";
      onChange({ ...block, additional_text: defaultText });
    }
  }, [sectionSlug, text]);

  // Pre-populate Paragraph 2 Circumstances of Loss for Apple, Pear, Mandarin, Grapes & Plum
  const isMandarin = ['mandarin', 'mandarins'].includes(commodityKey);
  const isGrapes = ['grape', 'grapes'].includes(commodityKey);
  const isPlum = ['plum', 'plums'].includes(commodityKey);
  const isCircumstancesFruit = ['apple', 'pear', 'mandarin', 'mandarins', 'grape', 'grapes', 'plum', 'plums'].includes(commodityKey);
  useEffect(() => {
    if (isCircumstancesFruit && isCircumstances && onChange) {
      if (!text.trim() && clauseContext) {
        let defaultText = '';
        if (isMandarin) {
          defaultText = buildMandarinCircumstances(clauseContext);
        } else if (isGrapes) {
          defaultText = buildGrapesCircumstances(clauseContext);
        } else if (isPlum) {
          defaultText = buildPlumCircumstances(clauseContext);
        } else {
          defaultText = buildCircumstancesText(clauseContext, commodityKey === 'pear' ? 'Pear' : 'Apple');
        }
        onChange({ ...block, additional_text: defaultText });
      } else if (text.includes('[') && clauseContext) {
        const filled = fillCircumstancesBlanks(text, clauseContext);
        if (filled !== text) {
          onChange({ ...block, additional_text: filled });
        }
      }
    }
  }, [commodityKey, isMandarin, isGrapes, isPlum, isCircumstancesFruit, isCircumstances, text, clauseContext]);

  // Pre-populate Note block for Mandarin (Reports M-165 & M-166)
  const isNoteBlock = block.id === 'b_note' || sectionSlug === 'note' || /^note:?$/i.test(sectionTitle.trim());
  useEffect(() => {
    if (isMandarin && isNoteBlock && !text.trim() && onChange) {
      onChange({ ...block, additional_text: MANDARIN_NOTE_TEXT });
    }
  }, [isMandarin, isNoteBlock, text]);

  // Pre-populate Paragraph 2.1 Our Survey for Apple, Pear, Mandarin, Grapes & Plum
  const isOurSurvey =
    block.id === 'b_para2_1' ||
    sectionSlug === 'survey_findings' ||
    /paragraph 2\.1|our survey/i.test(sectionTitle);
  const isOurSurveyFruit = ['apple', 'pear', 'mandarin', 'mandarins', 'grape', 'grapes', 'plum', 'plums'].includes(commodityKey);
  useEffect(() => {
    if (isOurSurveyFruit && isOurSurvey && onChange) {
      if (!text.trim() && clauseContext) {
        let defaultText = '';
        if (isMandarin) {
          defaultText = buildMandarinOurSurvey(clauseContext);
        } else if (isGrapes) {
          defaultText = buildGrapesOurSurvey(clauseContext);
        } else if (isPlum) {
          defaultText = buildPlumOurSurvey(clauseContext);
        } else if (commodityKey === 'pear') {
          defaultText = buildPearOurSurvey(clauseContext);
        } else {
          defaultText = buildAppleOurSurvey(clauseContext);
        }
        onChange({ ...block, additional_text: defaultText });
      } else if (text.includes('[') && clauseContext) {
        const filled = fillOurSurveyBlanks(text, clauseContext);
        if (filled !== text) {
          onChange({ ...block, additional_text: filled });
        }
      }
    }
  }, [commodityKey, isMandarin, isGrapes, isPlum, isOurSurveyFruit, isOurSurvey, text, clauseContext]);

  // Auto-populate or sync attendance for Application section
  useEffect(() => {
    if (sectionSlug === 'application' && onChange) {
      if (!block.attendance || block.attendance.length === 0) {
        const defaultRows = getDefaultAttendance(consigneeName);
        onChange({
          ...block,
          attendance: defaultRows,
          attendance_intro: block.attendance_intro || 'The following persons attended the survey:',
        });
      } else if (consigneeName) {
        const matched = lookupConsigneeStaff(consigneeName);
        if (matched.length > 0) {
          // Check if current attendance already contains this matched staff
          const alreadyHasStaff = matched.every((m) =>
            (block.attendance || []).some(
              (r: any) =>
                r.name.trim().toLowerCase() === m.name.trim().toLowerCase() &&
                r.representing.trim().toLowerCase() === m.representing.trim().toLowerCase()
            )
          );
          if (!alreadyHasStaff) {
            // Keep MCA surveyor and any non-consignee joint surveyors, replace old consignee staff
            const nonConsigneeRows = (block.attendance || []).filter((r: any) => {
              const rep = (r.representing || '').toLowerCase();
              const isMCA = rep.includes('marine cargo agencies') || r.name?.includes('Baburao');
              const isLineOrShipper =
                rep.includes('shipping line') ||
                rep.includes('shipper') ||
                rep.includes('insurer') ||
                rep.includes('underwriter') ||
                rep.includes('wan hai') ||
                rep.includes('oocl');
              return isMCA || isLineOrShipper;
            });
            if (
              !nonConsigneeRows.some(
                (r: any) =>
                  (r.representing || '').toLowerCase().includes('marine cargo agencies') ||
                  r.name?.includes('Baburao')
              )
            ) {
              nonConsigneeRows.push({
                name: 'Mr. Baburao Bhosale',
                designation: 'Surveyor',
                representing: 'Marine Cargo Agencies Pvt.Ltd (On behalf of Consignees)',
              });
            }
            onChange({
              ...block,
              attendance: [...matched, ...nonConsigneeRows],
            });
          }
        }
      }
    }
  }, [sectionSlug, consigneeName]);

  // Split and highlight bracketed photo references (Photo Nos?...)
  const renderFormattedText = (content: string) => {
    const parts = content.split(/(\(Photo Nos?\. [^\)]+\))/g);
    return parts.map((part, i) => {
      if (/^\(Photo Nos?\. [^\)]+\)$/.test(part)) {
        return (
          <span key={i} className="font-mono font-bold text-[#00387A]">
            {part}
          </span>
        );
      }
      return part;
    });
  };

  const paragraphs = text.split('\n\n').filter(Boolean);

  return (
    <div className="narrative-block my-2">
      {sectionTitle && (
        <h2 className="text-[12px] font-bold text-[#00387A] uppercase tracking-wider border-b border-slate-300 pb-1 mb-2">
          {sectionTitle}
        </h2>
      )}
      {editable && onChange ? (
        <>
          {/* Standard wording option cards: ONLY in Form Editor */}
          {/* Option card picker for curated fruits (apple, grapes, plum, pear, mandarin) kept commented out per user request:
          {isFormEditor && clauseContext && isCuratedFruit && (
            <ClausePicker
              sectionHeading={sectionTitle}
              section={clauseSection}
              context={clauseContext}
              added={addedTopics}
              onAdd={handleAddTopic}
              onRemove={handleRemoveTopic}
            />
          )}
          */}
          {isFormEditor && clauseContext && !hideClausePicker && (
            <ClausePicker
              sectionHeading={sectionTitle}
              section={clauseSection}
              context={clauseContext}
              added={addedTopics}
              onAdd={handleAddTopic}
              onRemove={handleRemoveTopic}
            />
          )}

          {/* Cold storage facility selector & auto-fill ONLY in Form Editor */}
          {isFormEditor && sectionSlug === 'application' && (
            <ColdStorageSelector
              currentText={text}
              onUpdateText={(updatedText) =>
                onChange({
                  ...block,
                  additional_text: updatedText,
                  surveyor_edited: true,
                })
              }
            />
          )}

          <textarea
            ref={textareaRef}
            value={text}
            onChange={handleTextChange}
            placeholder={
              isFormEditor
                ? hideClausePicker
                  ? 'Fill in the blanks and edit this section…'
                  : sectionSlug === 'general'
                  ? 'Type this section…'
                  : 'Type this section, or add standard wording above…'
                : ''
            }
            className={`w-full bg-transparent outline-none rounded text-xs leading-relaxed text-slate-800 text-justify font-sans resize-none overflow-hidden transition-colors cursor-text ${
              isFormEditor
                ? 'border border-transparent hover:border-blue-200 focus:border-blue-500 focus:bg-white p-1'
                : 'border-none p-0 focus:bg-blue-50/30'
            }`}
          />

          {sectionSlug === 'application' && (
            <ApplicationAttendance
              rows={block.attendance || []}
              intro={block.attendance_intro || 'The following persons attended the survey:'}
              consigneeName={consigneeName}
              vesselName={vesselName}
              editable={true}
              isFormEditor={isFormEditor}
              onChange={(newRows, newIntro) =>
                onChange({
                  ...block,
                  attendance: newRows,
                  attendance_intro: newIntro,
                  surveyor_edited: true,
                })
              }
            />
          )}

          {isFormEditor && clauseContext?.commodity === 'GENERAL_CARGO' && sectionSlug !== 'general' && (
            <NotesWriter
              section={sectionSlug}
              context={clauseContext}
              onAdd={(added) =>
                onChange({
                  ...block,
                  additional_text: [text.trim(), added.trim()].filter(Boolean).join('\n\n'),
                  surveyor_edited: true,
                })
              }
            />
          )}

          {clauseContext && blanks.length > 0 && isFormEditor && (
            <div className="mt-1 text-[10px] text-amber-800 bg-amber-50 border border-amber-200 rounded px-2 py-1">
              {blanks.length} blank{blanks.length > 1 ? 's' : ''} to fill in:{' '}
              <WithBlanks text={blanks.join(' ')} />
            </div>
          )}
        </>
      ) : (
        <div className="space-y-2 text-xs leading-relaxed text-slate-800 text-justify">
          {paragraphs.length > 0 ? (
            paragraphs.map((p: string, idx: number) => (
              <p key={idx} className="whitespace-pre-line">{renderFormattedText(p)}</p>
            ))
          ) : (
            <p>{renderFormattedText(text)}</p>
          )}

          {sectionSlug === 'application' && block.attendance && block.attendance.length > 0 && (
            <ApplicationAttendance
              rows={block.attendance}
              intro={block.attendance_intro || 'The following persons attended the survey:'}
              editable={false}
              isFormEditor={false}
              onChange={() => {}}
            />
          )}
        </div>
      )}
    </div>
  );
};


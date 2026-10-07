import React, { useRef, useLayoutEffect, useEffect, useState } from 'react';
import { ClausePicker, WithBlanks, detectSectionFromHeading } from '../../clauses/ClausePicker';
import { NotesWriter } from '../../clauses/NotesWriter';
import { ColdStorageSelector } from '../../clauses/ColdStorageSelector';
import { ApplicationAttendance } from '../../clauses/ApplicationAttendance';
import { defaultSurveyor, getDefaultAttendance, isMcaAttendee, lookupConsigneeStaff } from '../../../utils/staffLookup';
import { useReferenceData } from '../../../utils/referenceData';
import { Piece, RichPart, RichText, headingText, useHouseStyle } from '../../../utils/houseStyle';
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
  buildParagraph3CauseOfLoss,
  buildParagraph3Preamble,
  fillCauseOfLossBlanks,
  detectCauseCondition,
  type CauseCondition,
  buildParagraph4NextStep,
  detectNextStepAction,
  type NextStepAction,
  buildParagraph5Documentation,
  STANDARD_DOCUMENT_OPTIONS,
  detectActiveDocIds,
  detectPhotoDelivery,
  type PhotoDeliveryMode,
} from '../../../utils/clauseContext';
import { RecordersBlock } from './RecordersBlock';

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
  /**
   * Survey report preview only: print one part of Paragraph 3 so the pages can
   * break between its recorders — 'head' (heading and opening paragraph) or
   * 'tail' (the text after the recorders). The recorders are drawn on their own.
   */
  part?: 'head' | 'tail';
  /**
   * Survey report preview: print only these pieces of the section (heading,
   * paragraphs, recorders, attendance), so pages break between paragraphs.
   * A click on one asks the preview to open the whole section (onEditStart).
   */
  pieces?: Piece[];
  onEditStart?: (field: 'additional_text' | 'preamble') => void;
  /** Open this text for editing straight away; onEditEnd when it is left. */
  editField?: 'additional_text' | 'preamble';
  onEditEnd?: () => void;
  /** Optional temperature recorders block embedded inside Paragraph 3 */
  recordersBlock?: any;
  onRecordersChange?: (updatedRecordersBlock: any) => void;
  reportId?: string;
  onAttendanceChange?: (attendance: any[], intro?: string) => void;
}

export const NarrativeBlock: React.FC<NarrativeBlockProps> = ({
  block,
  onChange,
  editable = true,
  clauseContext,
  heading,
  clauseSection,
  isFormEditor = false,
  part,
  pieces,
  onEditStart,
  editField,
  onEditEnd,
  recordersBlock,
  onRecordersChange,
  reportId,
}) => {
  const sectionTitle = heading || block?._heading || block?.section || 'ATTENDANCE & CIRCUMSTANCES';
  const text = block?.additional_text || '';
  const preamble = block?.preamble || '';
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const preambleTextareaRef = useRef<HTMLTextAreaElement | null>(null);
  // A4 preview of a survey report: the text shows as printed (bold, underline,
  // sub-headings, bullets); a click turns it into the text box to edit.
  const house = useHouseStyle();
  const [editingField, setEditingField] = useState<null | 'additional_text' | 'preamble'>(editField ?? null);
  const stopEditing = () => {
    setEditingField(null);
    onEditEnd?.();
  };

  // useLayoutEffect fires synchronously after DOM mutation but before browser paint,
  // so the resize happens immediately even when text is set programmatically
  // (e.g. clause insertion), preventing overflow-hidden from clipping content.
  useLayoutEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.max(80, el.scrollHeight)}px`;
  }, [text, editable, editingField]);

  useLayoutEffect(() => {
    const el = preambleTextareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.max(60, el.scrollHeight)}px`;
  }, [preamble, editable, editingField]);

  if (!text && !preamble && !sectionTitle && !editable) return null;

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    if (!onChange) return;
    onChange({
      ...block,
      additional_text: e.target.value,
      surveyor_edited: true,
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      const textarea = textareaRef.current;
      if (!textarea) return;
      const pos = textarea.selectionStart;
      const currentText = textarea.value;
      const beforeCursor = currentText.substring(0, pos);
      const afterCursor = currentText.substring(pos);
      const lastLine = beforeCursor.split('\n').pop() || '';

      const bulletMatch = lastLine.match(/^(\s*)(•|-|\*)\s+/);
      const numMatch = lastLine.match(/^(\s*)(\d+)([\.\)])\s+/);

      if (bulletMatch) {
        if (lastLine.trim() === bulletMatch[2]) {
          // Empty bullet line: clear it on Enter (exit list)
          e.preventDefault();
          const lineStart = pos - lastLine.length;
          const next = currentText.substring(0, lineStart) + '\n' + afterCursor;
          onChange?.({ ...block, additional_text: next, surveyor_edited: true });
          setTimeout(() => {
            if (textareaRef.current) {
              textareaRef.current.selectionStart = lineStart + 1;
              textareaRef.current.selectionEnd = lineStart + 1;
            }
          }, 0);
          return;
        }
        e.preventDefault();
        const prefix = bulletMatch[1] + bulletMatch[2] + ' ';
        const next = beforeCursor + '\n' + prefix + afterCursor;
        onChange?.({ ...block, additional_text: next, surveyor_edited: true });
        setTimeout(() => {
          if (textareaRef.current) {
            textareaRef.current.selectionStart = pos + 1 + prefix.length;
            textareaRef.current.selectionEnd = pos + 1 + prefix.length;
          }
        }, 0);
        return;
      } else if (numMatch) {
        const nextNum = parseInt(numMatch[2], 10) + 1;
        const delim = numMatch[3];
        if (lastLine.trim() === `${numMatch[2]}${delim}`) {
          // Empty numbered line: clear it on Enter (exit list)
          e.preventDefault();
          const lineStart = pos - lastLine.length;
          const next = currentText.substring(0, lineStart) + '\n' + afterCursor;
          onChange?.({ ...block, additional_text: next, surveyor_edited: true });
          setTimeout(() => {
            if (textareaRef.current) {
              textareaRef.current.selectionStart = lineStart + 1;
              textareaRef.current.selectionEnd = lineStart + 1;
            }
          }, 0);
          return;
        }
        e.preventDefault();
        const prefix = `${numMatch[1]}${nextNum}${delim} `;
        const next = beforeCursor + '\n' + prefix + afterCursor;
        onChange?.({ ...block, additional_text: next, surveyor_edited: true });
        setTimeout(() => {
          if (textareaRef.current) {
            textareaRef.current.selectionStart = pos + 1 + prefix.length;
            textareaRef.current.selectionEnd = pos + 1 + prefix.length;
          }
        }, 0);
        return;
      }
    }
  };

  const handleInsertBullet = () => {
    const el = textareaRef.current;
    if (!el || !onChange) return;
    const pos = el.selectionStart;
    const cur = el.value;
    const before = cur.substring(0, pos);
    const after = cur.substring(pos);
    const needNewline = before.length > 0 && !before.endsWith('\n');
    const insertion = needNewline ? '\n• ' : '• ';
    const next = before + insertion + after;
    onChange({ ...block, additional_text: next, surveyor_edited: true });
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        textareaRef.current.selectionStart = pos + insertion.length;
        textareaRef.current.selectionEnd = pos + insertion.length;
      }
    }, 0);
  };

  const handleInsertNumber = () => {
    const el = textareaRef.current;
    if (!el || !onChange) return;
    const pos = el.selectionStart;
    const cur = el.value;
    const before = cur.substring(0, pos);
    const after = cur.substring(pos);
    const lines = before.split('\n');
    let nextNum = 1;
    for (let i = lines.length - 1; i >= 0; i--) {
      const m = lines[i].match(/^\s*(\d+)[\.\)]\s+/);
      if (m) {
        nextNum = parseInt(m[1], 10) + 1;
        break;
      }
    }
    const needNewline = before.length > 0 && !before.endsWith('\n');
    const insertion = needNewline ? `\n${nextNum}) ` : `${nextNum}) `;
    const next = before + insertion + after;
    onChange({ ...block, additional_text: next, surveyor_edited: true });
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        textareaRef.current.selectionStart = pos + insertion.length;
        textareaRef.current.selectionEnd = pos + insertion.length;
      }
    }, 0);
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
  const isNextStep =
    block.id === 'b_next_step' ||
    sectionSlug === 'next_step' ||
    /paragraph 4|next step/i.test(sectionTitle);
  const currentNextStepAction: NextStepAction =
    block.next_step_action || detectNextStepAction(text);

  const isDocumentation =
    block.id === 'b_doc' ||
    block.id === 'b_documentation' ||
    sectionSlug === 'documentation' ||
    /paragraph 5|documentation/i.test(sectionTitle);
  const currentActiveDocIds: string[] =
    block.selected_doc_ids || (text ? detectActiveDocIds(text) : []);
  const currentPhotoDelivery: PhotoDeliveryMode =
    block.photo_delivery || (text ? detectPhotoDelivery(text) : 'dropbox');

  const hideClausePicker = sectionSlug === 'application' || isCuratedFruit || isNextStep || isDocumentation;
  const isCircumstances = sectionSlug === 'circumstances_of_loss' || /circumstance/i.test(sectionTitle);

  const consigneeName = String(clauseContext?.values?.consignee || '');
  const referenceReady = useReferenceData();
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

  // Pre-populate Paragraph 3 Cause of Loss for Apple, Pear, Mandarin, Grapes & Plum
  const isCauseOfLoss =
    block.id === 'b_cause' ||
    sectionSlug === 'cause_of_loss' ||
    /cause of loss/i.test(sectionTitle);
  const isCauseFruit = isCuratedFruit;

  const currentCondition: CauseCondition =
    block.cause_condition ||
    (clauseContext ? detectCauseCondition(clauseContext, block) : 'no_recorder_data');

  useEffect(() => {
    if (isCauseFruit && isCauseOfLoss && onChange && clauseContext) {
      let needsUpdate = false;
      const updates: any = {};

      if (currentCondition !== 'no_recorder_data') {
        if (!preamble.trim() || !preamble.includes('requested temperature for this shipment of fresh')) {
          const rawPreamble = buildParagraph3Preamble(clauseContext);
          updates.preamble = fillCauseOfLossBlanks(rawPreamble, clauseContext);
          needsUpdate = true;
        } else if (preamble.includes('[')) {
          const filledPreamble = fillCauseOfLossBlanks(preamble, clauseContext);
          if (filledPreamble !== preamble) {
            updates.preamble = filledPreamble;
            needsUpdate = true;
          }
        }
      }

      const isOldStub =
        text.includes('While the Bill of Lading stipulated a mandatory carriage temperature') ||
        (currentCondition === 'carrier_breach' && !text.includes('Carriage Instructions:')) ||
        (currentCondition === 'cold_chain_complied' && !text.includes('Findings & Assessment:')) ||
        (currentCondition === 'no_recorder_data' && !text.includes('unable to download'));

      if (!text.trim() || isOldStub) {
        const rawTemplate = buildParagraph3CauseOfLoss(clauseContext, currentCondition);
        updates.additional_text = fillCauseOfLossBlanks(rawTemplate, clauseContext);
        updates.cause_condition = currentCondition;
        needsUpdate = true;
      } else if (text.includes('[')) {
        const filled = fillCauseOfLossBlanks(text, clauseContext);
        if (filled !== text) {
          updates.additional_text = filled;
          needsUpdate = true;
        }
      }

      if (needsUpdate) {
        onChange({ ...block, ...updates });
      }
    }
  }, [commodityKey, isCauseFruit, isCauseOfLoss, text, preamble, clauseContext, currentCondition]);

  // Pre-populate Paragraph 4 Next Step for Apple, Pear, Mandarin, Grapes & Plum
  useEffect(() => {
    if (isCuratedFruit && isNextStep && onChange && clauseContext) {
      if (!text.trim()) {
        const defaultText = buildParagraph4NextStep(clauseContext, undefined, currentNextStepAction);
        onChange({
          ...block,
          additional_text: defaultText,
          next_step_action: currentNextStepAction,
        });
      }
    }
  }, [commodityKey, isCuratedFruit, isNextStep, text, clauseContext, currentNextStepAction]);

  const handleNextStepActionSwitch = (newAction: NextStepAction) => {
    if (!onChange || !clauseContext) return;
    const newText = buildParagraph4NextStep(clauseContext, undefined, newAction);
    onChange({
      ...block,
      additional_text: newText,
      next_step_action: newAction,
      surveyor_edited: true,
    });
  };

  // Auto-sync Paragraph 5 Documentation from particulars, recorders, attendance, and photos if unedited
  useEffect(() => {
    if (isDocumentation && onChange && clauseContext) {
      const isUnedited = !text.trim() || !block.surveyor_edited;
      if (isUnedited) {
        const syncedText = buildParagraph5Documentation(clauseContext, undefined, currentPhotoDelivery);
        if (syncedText !== text) {
          const syncedDocIds = detectActiveDocIds(syncedText);
          onChange({
            ...block,
            additional_text: syncedText,
            selected_doc_ids: syncedDocIds,
            photo_delivery: currentPhotoDelivery,
          });
        }
      }
    }
  }, [
    isDocumentation,
    block.surveyor_edited,
    text,
    clauseContext?.values?.invoice_no,
    clauseContext?.values?.policy_no,
    clauseContext?.values?.has_recorders,
    clauseContext?.values?.has_joint_survey,
    clauseContext?.values?.photo_count,
    currentPhotoDelivery,
  ]);

  const handleToggleDoc = (docId: string) => {
    if (!onChange || !clauseContext) return;
    const currentList = currentActiveDocIds.length > 0 ? currentActiveDocIds : detectActiveDocIds(text);
    const nextList = currentList.includes(docId)
      ? currentList.filter((id) => id !== docId)
      : [...currentList, docId];
    const newText = buildParagraph5Documentation(clauseContext, nextList, currentPhotoDelivery);
    onChange({
      ...block,
      additional_text: newText,
      selected_doc_ids: nextList,
      surveyor_edited: true,
    });
  };

  const handlePhotoDeliverySwitch = (newDelivery: PhotoDeliveryMode) => {
    if (!onChange || !clauseContext) return;
    const currentList = currentActiveDocIds.length > 0 ? currentActiveDocIds : detectActiveDocIds(text);
    const newText = buildParagraph5Documentation(clauseContext, currentList, newDelivery);
    onChange({
      ...block,
      additional_text: newText,
      photo_delivery: newDelivery,
      surveyor_edited: true,
    });
  };

  const handleDocRegenerate = () => {
    if (!onChange || !clauseContext) return;
    const newText = buildParagraph5Documentation(clauseContext, undefined, currentPhotoDelivery);
    const detected = detectActiveDocIds(newText);
    onChange({
      ...block,
      additional_text: newText,
      selected_doc_ids: detected,
      surveyor_edited: true,
    });
  };

  const handleConditionSwitch = (newCondition: CauseCondition) => {
    if (!onChange || !clauseContext) return;
    const rawTemplate = buildParagraph3CauseOfLoss(clauseContext, newCondition);
    const newText = fillCauseOfLossBlanks(rawTemplate, clauseContext);

    let newPreamble = '';
    if (newCondition !== 'no_recorder_data') {
      const rawPreamble = buildParagraph3Preamble(clauseContext);
      newPreamble = fillCauseOfLossBlanks(rawPreamble, clauseContext);
    }

    onChange({
      ...block,
      preamble: newPreamble,
      additional_text: newText,
      cause_condition: newCondition,
      surveyor_edited: true,
    });

    if (onRecordersChange && recordersBlock) {
      onRecordersChange({
        ...recordersBlock,
        included: newCondition !== 'no_recorder_data',
      });
    }
  };

  /**
   * Marks for the printed report: **bold**, __underline__, and "## " in front
   * of a line for a sub-heading. With nothing selected the marks go in empty,
   * with the cursor between them.
   */
  const wrapSelectionIn = (
    targetRef: React.RefObject<HTMLTextAreaElement | null>,
    mark: '**' | '__' | '## ',
    field: 'preamble' | 'additional_text' = 'additional_text'
  ) => {
    const textarea = targetRef.current;
    const currentVal = (field === 'preamble' ? block?.preamble : block?.additional_text) || '';
    const start = textarea ? textarea.selectionStart : currentVal.length;
    const end = textarea ? textarea.selectionEnd : currentVal.length;
    let newText: string;
    let caret: number;
    if (mark === '## ') {
      const lineStart = currentVal.lastIndexOf('\n', start - 1) + 1;
      const line = currentVal.slice(lineStart);
      const has = line.startsWith('## ');
      newText = has ? currentVal.slice(0, lineStart) + line.slice(3) : currentVal.slice(0, lineStart) + '## ' + line;
      caret = has ? Math.max(lineStart, start - 3) : start + 3;
    } else {
      newText = currentVal.slice(0, start) + mark + currentVal.slice(start, end) + mark + currentVal.slice(end);
      caret = end === start ? start + mark.length : end + 2 * mark.length;
    }
    onChange?.({ ...block, [field]: newText, surveyor_edited: true });
    setTimeout(() => {
      if (!textarea) return;
      textarea.focus();
      textarea.setSelectionRange(caret, caret);
    }, 0);
  };

  const markButtons = (targetRef: React.RefObject<HTMLTextAreaElement | null>, field: 'preamble' | 'additional_text') => (
    <>
      <button
        type="button"
        onMouseDown={(e) => e.preventDefault()}
        onClick={() => wrapSelectionIn(targetRef, '**', field)}
        className="px-2 py-0.5 bg-white hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300 border border-slate-200 rounded font-bold transition-colors cursor-pointer text-slate-700"
        title="Bold: select words and click (prints in bold)"
      >
        B
      </button>
      <button
        type="button"
        onMouseDown={(e) => e.preventDefault()}
        onClick={() => wrapSelectionIn(targetRef, '__', field)}
        className="px-2 py-0.5 bg-white hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300 border border-slate-200 rounded underline transition-colors cursor-pointer text-slate-700"
        title="Underline: select words and click (prints underlined)"
      >
        U
      </button>
      <button
        type="button"
        onMouseDown={(e) => e.preventDefault()}
        onClick={() => wrapSelectionIn(targetRef, '## ', field)}
        className="px-2 py-0.5 bg-white hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300 border border-slate-200 rounded font-semibold transition-colors cursor-pointer text-[#002060]"
        title="Sub-heading: the line the cursor is on prints bold, underlined, dark blue"
      >
        Heading
      </button>
      <span className="text-[10px] text-slate-400 ml-1">**bold** __underline__ ## heading</span>
    </>
  );

  const insertAtCursorIn = (
    targetRef: React.RefObject<HTMLTextAreaElement | null>,
    insertion: string,
    field: 'preamble' | 'additional_text' = 'additional_text'
  ) => {
    const textarea = targetRef.current;
    const currentVal = (field === 'preamble' ? block?.preamble : block?.additional_text) || '';
    if (!textarea) {
      onChange?.({
        ...block,
        [field]: currentVal ? `${currentVal}\n${insertion}` : insertion,
        surveyor_edited: true,
      });
      return;
    }
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const before = currentVal.substring(0, start);
    const after = currentVal.substring(end);
    const needsNewline = before.length > 0 && !before.endsWith('\n');
    const prefix = needsNewline ? '\n' : '';
    const newText = before + prefix + insertion + after;
    onChange?.({
      ...block,
      [field]: newText,
      surveyor_edited: true,
    });
    setTimeout(() => {
      textarea.focus();
      const newPos = start + prefix.length + insertion.length;
      textarea.setSelectionRange(newPos, newPos);
    }, 0);
  };

  const handleKeyDownIn = (
    e: React.KeyboardEvent<HTMLTextAreaElement>,
    targetRef: React.RefObject<HTMLTextAreaElement | null>,
    field: 'preamble' | 'additional_text'
  ) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      const textarea = targetRef.current;
      if (!textarea) return;
      const pos = textarea.selectionStart;
      const currentText = textarea.value;
      const beforeCursor = currentText.substring(0, pos);
      const afterCursor = currentText.substring(pos);
      const lastLine = beforeCursor.split('\n').pop() || '';

      const bulletMatch = lastLine.match(/^(\s*)(•|-|\*)\s+/);
      const numMatch = lastLine.match(/^(\s*)(\d+)([\.\)])\s+/);

      if (bulletMatch) {
        if (lastLine.trim() === bulletMatch[2]) {
          e.preventDefault();
          const lineStart = pos - lastLine.length;
          const next = currentText.substring(0, lineStart) + '\n' + afterCursor;
          onChange?.({ ...block, [field]: next, surveyor_edited: true });
          setTimeout(() => {
            if (targetRef.current) {
              targetRef.current.selectionStart = lineStart + 1;
              targetRef.current.selectionEnd = lineStart + 1;
            }
          }, 0);
          return;
        }
        e.preventDefault();
        const indent = bulletMatch[1];
        const next = beforeCursor + '\n' + indent + '• ' + afterCursor;
        onChange?.({ ...block, [field]: next, surveyor_edited: true });
        setTimeout(() => {
          if (targetRef.current) {
            const nextPos = pos + indent.length + 3;
            targetRef.current.selectionStart = nextPos;
            targetRef.current.selectionEnd = nextPos;
          }
        }, 0);
        return;
      }

      if (numMatch) {
        const currentNum = parseInt(numMatch[2], 10);
        const delimiter = numMatch[3];
        if (lastLine.trim() === `${currentNum}${delimiter}`) {
          e.preventDefault();
          const lineStart = pos - lastLine.length;
          const next = currentText.substring(0, lineStart) + '\n' + afterCursor;
          onChange?.({ ...block, [field]: next, surveyor_edited: true });
          setTimeout(() => {
            if (targetRef.current) {
              targetRef.current.selectionStart = lineStart + 1;
              targetRef.current.selectionEnd = lineStart + 1;
            }
          }, 0);
          return;
        }
        e.preventDefault();
        const indent = numMatch[1];
        const nextNum = currentNum + 1;
        const next = beforeCursor + '\n' + indent + `${nextNum}${delimiter} ` + afterCursor;
        onChange?.({ ...block, [field]: next, surveyor_edited: true });
        setTimeout(() => {
          if (targetRef.current) {
            const nextPos = pos + indent.length + String(nextNum).length + delimiter.length + 2;
            targetRef.current.selectionStart = nextPos;
            targetRef.current.selectionEnd = nextPos;
          }
        }, 0);
      }
    }
  };

  // Auto-populate or sync attendance for Application section
  // (runs again once the staff list has arrived from the server)
  useEffect(() => {
    if (sectionSlug === 'application' && onChange && referenceReady) {
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
              const isMCA = isMcaAttendee(r);
              const isLineOrShipper =
                rep.includes('shipping line') ||
                rep.includes('shipper') ||
                rep.includes('insurer') ||
                rep.includes('underwriter') ||
                rep.includes('wan hai') ||
                rep.includes('oocl');
              return isMCA || isLineOrShipper;
            });
            const surveyor = defaultSurveyor();
            if (surveyor && !nonConsigneeRows.some(isMcaAttendee)) {
              nonConsigneeRows.push(surveyor);
            }
            onChange({
              ...block,
              attendance: [...matched, ...nonConsigneeRows],
            });
          }
        }
      }
    }
  }, [sectionSlug, consigneeName, referenceReady]);

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
  const houseView = house && !isFormEditor;

  // As in the Word file: no heading over nothing (a Note with no note).
  if (houseView) {
    const hasPeople = (block?.attendance || []).some((r: any) =>
      ['name', 'designation', 'representing'].some((k) => String(r?.[k] || '').trim())
    );
    const hasRecorders = isCauseOfLoss && (recordersBlock?.recorders || []).length > 0 && recordersBlock?.included !== false;
    if (!text.trim() && !preamble.trim() && !hasPeople && !hasRecorders) return null;
    if (part === 'tail' && !text.trim()) return null;
  }

  /** In the A4 preview the text shows as printed until it is clicked. */
  const previewText = (field: 'additional_text' | 'preamble', value: string, box: React.ReactNode) =>
    houseView && editingField !== field ? (
      <div
        className="cursor-text rounded hover:bg-blue-50/40"
        title="Click to edit"
        onClick={() => editable && onChange && (onEditStart ? onEditStart(field) : setEditingField(field))}
        data-testid={`rich-${field}`}
      >
        {value.trim() ? <RichText text={value} fruit={commodityKey} /> : <p className="mca-p text-slate-400">Click to type…</p>}
      </div>
    ) : (
      box
    );

  if (houseView && pieces) {
    const clickable = (field: 'additional_text' | 'preamble', node: React.ReactNode, key: number) => (
      <div
        key={key}
        className={editable && onChange ? 'cursor-text rounded hover:bg-blue-50/40' : ''}
        title={editable && onChange ? 'Click to edit' : undefined}
        onClick={() => editable && onChange && (onEditStart ? onEditStart(field) : setEditingField(field))}
        data-testid={`rich-${field}`}
      >
        {node}
      </div>
    );
    return (
      <div className="narrative-block">
        {pieces.map((pc, i) => {
          if (pc.kind === 'heading') return <p key={i} className="mca-heading">{headingText(sectionTitle)}</p>;
          if (pc.kind === 'pre') return clickable('preamble', <RichPart text={preamble} fruit={commodityKey} part={pc.part} />, i);
          if (pc.kind === 'text') return clickable('additional_text', <RichPart text={text} fruit={commodityKey} part={pc.part} />, i);
          if (pc.kind === 'rec') {
            return recordersBlock ? (
              <RecordersBlock key={i} block={recordersBlock} reportId={reportId} hideTitle only={pc.index} />
            ) : null;
          }
          return (
            <ApplicationAttendance
              key={i}
              rows={block.attendance || []}
              intro={block.attendance_intro || 'The following persons attended the survey:'}
              consigneeName={consigneeName}
              vesselName={vesselName}
              editable={Boolean(editable && onChange)}
              isFormEditor={false}
              onChange={(newRows, newIntro) =>
                onChange?.({ ...block, attendance: newRows, attendance_intro: newIntro, surveyor_edited: true })
              }
            />
          );
        })}
      </div>
    );
  }

  return (
    <div className={houseView ? 'narrative-block' : 'narrative-block my-2'}>
      {sectionTitle && houseView && part !== 'tail' && <p className="mca-heading">{headingText(sectionTitle)}</p>}
      {sectionTitle && !houseView && (
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

          {/* Cause condition 3-button segmented pill selector: ONLY in Form Editor for Cause of Loss */}
          {isFormEditor && isCauseFruit && isCauseOfLoss && (
            <div className="flex flex-wrap items-center justify-between gap-2 mb-3 p-2 bg-slate-50 border border-slate-200 rounded-lg">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                  Cause Condition:
                </span>
                <div className="inline-flex rounded-md shadow-xs" role="group">
                  <button
                    type="button"
                    onClick={() => handleConditionSwitch('carrier_breach')}
                    className={`px-3 py-1 text-xs font-semibold rounded-l-md border transition-colors cursor-pointer flex items-center gap-1.5 ${
                      currentCondition === 'carrier_breach'
                        ? 'bg-rose-600 text-white border-rose-600 z-10 shadow-xs'
                        : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100'
                    }`}
                    title="Carrier breach / transit thermal abuse"
                  >
                    <span>⚠️</span> Carrier Breach
                  </button>
                  <button
                    type="button"
                    onClick={() => handleConditionSwitch('cold_chain_complied')}
                    className={`px-3 py-1 text-xs font-semibold border-t border-b border-r transition-colors cursor-pointer flex items-center gap-1.5 ${
                      currentCondition === 'cold_chain_complied'
                        ? 'bg-sky-600 text-white border-sky-600 z-10 shadow-xs'
                        : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100'
                    }`}
                    title="Cold chain complied / inherent vice or delay"
                  >
                    <span>❄️</span> Cold-Chain Complied
                  </button>
                  <button
                    type="button"
                    onClick={() => handleConditionSwitch('no_recorder_data')}
                    className={`px-3 py-1 text-xs font-semibold rounded-r-md border transition-colors cursor-pointer flex items-center gap-1.5 ${
                      currentCondition === 'no_recorder_data'
                        ? 'bg-amber-600 text-white border-amber-600 z-10 shadow-xs'
                        : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100'
                    }`}
                    title="No recorder recovered or data unreadable"
                  >
                    <span>❌</span> No Recorder Data
                  </button>
                </div>
              </div>
              <span className="text-[10px] text-slate-400 italic">
                Clicking replaces narrative template cleanly
              </span>
            </div>
          )}

          {/* Paragraph 4 Next Step 2-button segmented pill selector: ONLY in Form Editor for Next Step */}
          {isFormEditor && isCuratedFruit && isNextStep && (
            <div className="flex flex-wrap items-center justify-between gap-2 mb-3 p-2 bg-slate-50 border border-slate-200 rounded-lg">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                  Next Step Action:
                </span>
                <div className="inline-flex rounded-md shadow-xs" role="group">
                  <button
                    type="button"
                    onClick={() => handleNextStepActionSwitch('prompt_sale')}
                    className={`px-3 py-1 text-xs font-semibold rounded-l-md border transition-colors cursor-pointer flex items-center gap-1.5 ${
                      currentNextStepAction === 'prompt_sale'
                        ? 'bg-blue-600 text-white border-blue-600 z-10 shadow-xs'
                        : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100'
                    }`}
                    title="Immediate prompt sale to mitigate loss"
                  >
                    <span>⚡</span> Prompt Sale / Mitigation
                  </button>
                  <button
                    type="button"
                    onClick={() => handleNextStepActionSwitch('bio_destruction')}
                    className={`px-3 py-1 text-xs font-semibold rounded-r-md border transition-colors cursor-pointer flex items-center gap-1.5 ${
                      currentNextStepAction === 'bio_destruction'
                        ? 'bg-rose-600 text-white border-rose-600 z-10 shadow-xs'
                        : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100'
                    }`}
                    title="Total loss / supervised bio-destruction & APMC disposal certificate (e.g. M-160)"
                  >
                    <span>🗑️</span> Supervised Bio-Destruction (Total Loss)
                  </button>
                </div>
              </div>
              <span className="text-[10px] text-slate-400 italic">
                Prompt sale vs. APMC bio-destruction
              </span>
            </div>
          )}

          {/* Paragraph 5 Documentation helper: ONLY in Form Editor for Documentation */}
          {isFormEditor && isDocumentation && (
            <div className="mb-3 p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-2.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                  Secured Documents Included:
                </span>
                <button
                  type="button"
                  onClick={handleDocRegenerate}
                  className="px-2 py-0.5 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded transition cursor-pointer flex items-center gap-1 shadow-2xs"
                  title="Re-detect from Particulars, Attendance, and Photo Plate"
                >
                  <span>🔄</span> Re-detect from Data & Photos
                </button>
              </div>

              {/* Document toggle chips */}
              <div className="flex flex-wrap gap-1.5">
                {STANDARD_DOCUMENT_OPTIONS.map((opt) => {
                  const isSelected = (currentActiveDocIds.length > 0 ? currentActiveDocIds : detectActiveDocIds(text)).includes(opt.id);
                  return (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => handleToggleDoc(opt.id)}
                      className={`px-2.5 py-1 text-xs font-medium rounded-md border transition cursor-pointer flex items-center gap-1.5 ${
                        isSelected
                          ? 'bg-blue-600 text-white border-blue-600 shadow-2xs'
                          : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-100 hover:text-slate-800'
                      }`}
                    >
                      <span>{isSelected ? '✓' : '+'}</span>
                      <span>{opt.label}</span>
                    </button>
                  );
                })}
              </div>

              {/* Photo delivery wording toggle */}
              <div className="flex flex-wrap items-center justify-between pt-1 border-t border-slate-200 text-xs">
                <span className="text-[10px] text-slate-500 font-semibold uppercase">Photo Delivery Phrasing:</span>
                <div className="inline-flex rounded-md shadow-2xs" role="group">
                  <button
                    type="button"
                    onClick={() => handlePhotoDeliverySwitch('dropbox')}
                    className={`px-2.5 py-0.5 text-xs font-medium rounded-l-md border transition cursor-pointer ${
                      currentPhotoDelivery === 'dropbox'
                        ? 'bg-slate-700 text-white border-slate-700'
                        : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-100'
                    }`}
                  >
                    ☁️ Dropbox Link
                  </button>
                  <button
                    type="button"
                    onClick={() => handlePhotoDeliverySwitch('zip')}
                    className={`px-2.5 py-0.5 text-xs font-medium rounded-r-md border transition cursor-pointer ${
                      currentPhotoDelivery === 'zip'
                        ? 'bg-slate-700 text-white border-slate-700'
                        : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-100'
                    }`}
                  >
                    📦 ZIP File
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Paragraph 3 with Recorders: Form Editor mode vs A4 HTML Preview mode */}
          {isCauseFruit && isCauseOfLoss && currentCondition !== 'no_recorder_data' ? (
            isFormEditor ? (
              <div className="space-y-4">
                {/* 1. Preamble Section */}
                <div className="bg-slate-50/50 p-2.5 rounded-lg border border-slate-200">
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="text-[11px] font-bold text-[#00387A] uppercase tracking-wide flex items-center gap-1.5">
                      <span>📜</span> Preamble (Carriage Instructions & Recorder Intake)
                    </div>
                    <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
                      <span className="text-[10px] font-semibold uppercase text-slate-400 mr-0.5">Insert:</span>
                      <button
                        type="button"
                        onClick={() => insertAtCursorIn(preambleTextareaRef, '• ', 'preamble')}
                        className="px-2 py-0.5 bg-white hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300 border border-slate-200 rounded font-medium transition-colors flex items-center gap-1 cursor-pointer text-slate-700 shadow-xs"
                      >
                        <span className="font-bold text-blue-600">•</span> Bullet
                      </button>
                      <button
                        type="button"
                        onClick={() => insertAtCursorIn(preambleTextareaRef, '1) ', 'preamble')}
                        className="px-2 py-0.5 bg-white hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300 border border-slate-200 rounded font-medium transition-colors flex items-center gap-1 cursor-pointer text-slate-700 shadow-xs"
                      >
                        <span className="font-bold text-blue-600">1)</span> Number
                      </button>
                      {markButtons(preambleTextareaRef, 'preamble')}
                    </div>
                  </div>
                  <textarea
                    ref={preambleTextareaRef}
                    value={preamble}
                    onChange={(e) =>
                      onChange?.({
                        ...block,
                        preamble: e.target.value,
                        surveyor_edited: true,
                      })
                    }
                    onKeyDown={(e) => handleKeyDownIn(e, preambleTextareaRef, 'preamble')}
                    placeholder="As per the Bill of Lading, the requested temperature for this shipment of fresh fruit was..."
                    className="w-full bg-white border border-slate-200 hover:border-blue-200 focus:border-blue-500 focus:bg-white rounded p-2 text-xs leading-relaxed text-slate-800 text-justify font-sans resize-none overflow-hidden transition-colors cursor-text shadow-xs"
                  />
                </div>

                {/* 2. Embedded Recorders Section (Tables & Graphs) */}
                {recordersBlock && onRecordersChange && (
                  <div className="bg-slate-50/50 p-2.5 rounded-lg border border-slate-200">
                    <RecordersBlock
                      block={recordersBlock}
                      reportId={reportId}
                      onChange={onRecordersChange}
                      hideTitle={true}
                      isFormEditor={true}
                    />
                  </div>
                )}

                {/* 3. Post-Graph Cause of Loss & Liability Assessment Section */}
                <div className="bg-slate-50/50 p-2.5 rounded-lg border border-slate-200">
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="text-[11px] font-bold text-[#00387A] uppercase tracking-wide flex items-center gap-1.5">
                      <span>⚖️</span> Cause of Loss & Liability Assessment (Post-Recorder Analysis)
                    </div>
                    <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
                      <span className="text-[10px] font-semibold uppercase text-slate-400 mr-0.5">Insert:</span>
                      <button
                        type="button"
                        onClick={() => insertAtCursorIn(textareaRef, '• ', 'additional_text')}
                        className="px-2 py-0.5 bg-white hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300 border border-slate-200 rounded font-medium transition-colors flex items-center gap-1 cursor-pointer text-slate-700 shadow-xs"
                      >
                        <span className="font-bold text-blue-600">•</span> Bullet
                      </button>
                      <button
                        type="button"
                        onClick={() => insertAtCursorIn(textareaRef, '1) ', 'additional_text')}
                        className="px-2 py-0.5 bg-white hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300 border border-slate-200 rounded font-medium transition-colors flex items-center gap-1 cursor-pointer text-slate-700 shadow-xs"
                      >
                        <span className="font-bold text-blue-600">1)</span> Number
                      </button>
                      {markButtons(textareaRef, 'additional_text')}
                    </div>
                  </div>
                  <textarea
                    ref={textareaRef}
                    value={text}
                    onChange={handleTextChange}
                    onKeyDown={handleKeyDown}
                    placeholder="Type cause of loss and liability assessment..."
                    className="w-full bg-white border border-slate-200 hover:border-blue-200 focus:border-blue-500 focus:bg-white rounded p-2 text-xs leading-relaxed text-slate-800 text-justify font-sans resize-none overflow-hidden transition-colors cursor-text shadow-xs"
                  />
                </div>
              </div>
            ) : (
              /* A4 HTML Preview Mode: Preamble -> Embedded Recorders -> Liability Assessment */
              <div className="space-y-3">
                {/* 1. Preamble */}
                {part === 'tail' ? null : editable ? previewText('preamble', preamble,
                  <textarea
                    ref={preambleTextareaRef}
                    autoFocus={houseView}
                    onBlur={() => houseView && stopEditing()}
                    value={preamble}
                    onChange={(e) =>
                      onChange?.({
                        ...block,
                        preamble: e.target.value,
                        surveyor_edited: true,
                      })
                    }
                    placeholder="As per the Bill of Lading, the requested temperature for this shipment of fresh fruit was..."
                    className={`w-full bg-transparent outline-none rounded resize-none overflow-hidden transition-colors cursor-text border-none p-0 focus:bg-blue-50/30 ${houseView ? 'mca-textarea' : 'text-xs leading-relaxed text-slate-800 text-justify font-sans'}`}
                  />
                ) : houseView ? (
                  preamble && <RichText text={preamble} fruit={commodityKey} />
                ) : (
                  preamble && <p className="whitespace-pre-line">{renderFormattedText(preamble)}</p>
                )}

                {/* 2. Embedded Recorders (Vertical Tables & Graph) */}
                {recordersBlock && !part && (
                  <RecordersBlock
                    block={recordersBlock}
                    reportId={reportId}
                    onChange={onRecordersChange}
                    hideTitle={true}
                    isFormEditor={false}
                  />
                )}

                {/* 3. Post-Graph Cause of Loss & Liability Assessment */}
                {part === 'head' ? null : editable ? previewText('additional_text', text,
                  <textarea
                    ref={textareaRef}
                    autoFocus={houseView}
                    onBlur={() => houseView && stopEditing()}
                    value={text}
                    onChange={handleTextChange}
                    onKeyDown={handleKeyDown}
                    placeholder="Type cause of loss and liability assessment..."
                    className={`w-full bg-transparent outline-none rounded resize-none overflow-hidden transition-colors cursor-text border-none p-0 focus:bg-blue-50/30 ${houseView ? 'mca-textarea' : 'text-xs leading-relaxed text-slate-800 text-justify font-sans'}`}
                  />
                ) : houseView ? (
                  <RichText text={text} fruit={commodityKey} />
                ) : paragraphs.length > 0 ? (
                  paragraphs.map((p: string, idx: number) => (
                    <p key={`post-${idx}`} className="whitespace-pre-line">{renderFormattedText(p)}</p>
                  ))
                ) : (
                  <p>{renderFormattedText(text)}</p>
                )}
              </div>
            )
          ) : (
            /* Standard single textarea editor (used for other sections or when no recorder data) */
            <>
              {isFormEditor && (
                <div className="flex items-center gap-1.5 mb-1.5 text-[11px] text-slate-500">
                  <span className="text-[10px] font-semibold uppercase text-slate-400 mr-0.5">Insert:</span>
                  <button
                    type="button"
                    onClick={handleInsertBullet}
                    className="px-2 py-0.5 bg-slate-50 hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300 border border-slate-200 rounded font-medium transition-colors flex items-center gap-1 cursor-pointer text-slate-700"
                    title="Insert a bullet point (•)"
                  >
                    <span className="font-bold text-blue-600">•</span> Bullet
                  </button>
                  <button
                    type="button"
                    onClick={handleInsertNumber}
                    className="px-2 py-0.5 bg-slate-50 hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300 border border-slate-200 rounded font-medium transition-colors flex items-center gap-1 cursor-pointer text-slate-700"
                    title="Insert a numbered point (1.)"
                  >
                    <span className="font-bold text-blue-600">1)</span> Number
                  </button>
                  {markButtons(textareaRef, 'additional_text')}
                </div>
              )}

              {previewText('additional_text', text, <textarea
                ref={textareaRef}
                autoFocus={houseView}
                onBlur={() => houseView && stopEditing()}
                value={text}
                onChange={handleTextChange}
                onKeyDown={handleKeyDown}
                placeholder={
                  isFormEditor
                    ? isDocumentation
                      ? 'Type documentation advice (e.g. bills of lading, packing lists, photo tallies)...'
                      : isNextStep
                      ? 'Type next step advice (e.g. prompt sale or supervised bio-destruction)...'
                      : hideClausePicker
                      ? 'Fill in the blanks and edit this section…'
                      : sectionSlug === 'general'
                      ? 'Type this section…'
                      : 'Type this section, or add standard wording above…'
                    : ''
                }
                className={`w-full bg-transparent outline-none rounded resize-none overflow-hidden transition-colors cursor-text ${
                  houseView ? 'mca-textarea' : 'text-xs leading-relaxed text-slate-800 text-justify font-sans'
                } ${
                  isFormEditor
                    ? 'border border-transparent hover:border-blue-200 focus:border-blue-500 focus:bg-white p-1'
                    : 'border-none p-0 focus:bg-blue-50/30'
                }`}
              />)}
            </>
          )}

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
        /* Preview Mode */
        houseView ? (
          <div>
            {preamble && part !== 'tail' && <RichText text={preamble} fruit={commodityKey} />}
            {isCauseFruit && isCauseOfLoss && currentCondition !== 'no_recorder_data' && recordersBlock && !part && (
              <RecordersBlock block={recordersBlock} reportId={reportId} hideTitle={true} />
            )}
            {part !== 'head' && <RichText text={text} fruit={commodityKey} />}
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
        ) : (
        <div className="space-y-2 text-xs leading-relaxed text-slate-800 text-justify">
          {isCauseFruit && isCauseOfLoss && currentCondition !== 'no_recorder_data' ? (
            <div className="space-y-3">
              {preamble && <p className="whitespace-pre-line">{renderFormattedText(preamble)}</p>}

              {recordersBlock && (
                <RecordersBlock block={recordersBlock} reportId={reportId} hideTitle={true} />
              )}

              {paragraphs.length > 0 ? (
                paragraphs.map((p: string, idx: number) => (
                  <p key={`post-${idx}`} className="whitespace-pre-line">{renderFormattedText(p)}</p>
                ))
              ) : (
                <p>{renderFormattedText(text)}</p>
              )}
            </div>
          ) : (
            <>
              {paragraphs.length > 0 ? (
                paragraphs.map((p: string, idx: number) => (
                  <p key={idx} className="whitespace-pre-line">{renderFormattedText(p)}</p>
                ))
              ) : (
                <p>{renderFormattedText(text)}</p>
              )}
            </>
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
        )
      )}
    </div>
  );
};


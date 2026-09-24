import React, { useRef, useLayoutEffect } from 'react';
import { ClausePicker, WithBlanks, detectSectionFromHeading } from '../../clauses/ClausePicker';
import type { ClauseContext } from '../../../api/client';
import { BLANK_PATTERN } from '../../../utils/clauseContext';

export interface NarrativeBlockProps {
  block: any;
  onChange?: (updatedBlock: any) => void;
  editable?: boolean;
  /** Fruit, container, measurements and counted defects, for the clause picker. */
  clauseContext?: ClauseContext;
}

export const NarrativeBlock: React.FC<NarrativeBlockProps> = ({
  block,
  onChange,
  editable = true,
  clauseContext,
}) => {
  const sectionTitle = block?.section || 'ATTENDANCE & CIRCUMSTANCES';
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

  const sectionSlug = detectSectionFromHeading(sectionTitle);
  const blanks = text.match(BLANK_PATTERN) || [];

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
          {clauseContext && (
            <ClausePicker
              sectionHeading={sectionTitle}
              context={clauseContext}
              added={addedTopics}
              onAdd={handleAddTopic}
              onRemove={handleRemoveTopic}
            />
          )}

          <textarea
            ref={textareaRef}
            value={text}
            onChange={handleTextChange}
            placeholder={
              sectionSlug === 'general'
                ? 'Type this section…'
                : 'Type this section, or add standard wording above…'
            }
            className="w-full bg-transparent border border-transparent hover:border-blue-200 focus:border-blue-500 focus:bg-white focus:outline-none rounded p-1 text-xs leading-relaxed text-slate-800 text-justify font-sans resize-none overflow-hidden transition-colors cursor-text"
          />

          {clauseContext && blanks.length > 0 && (
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
        </div>
      )}
    </div>
  );
};

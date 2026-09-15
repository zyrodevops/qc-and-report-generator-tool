import React, { useRef, useLayoutEffect } from 'react';
import { ClauseLibraryPicker } from './ClauseLibraryPicker';

export interface NarrativeBlockProps {
  block: any;
  onChange?: (updatedBlock: any) => void;
  editable?: boolean;
  /** Commodity key (e.g. "APPLE") passed down from ReportPreview via blockState.metadata */
  commodity?: string;
}

export const NarrativeBlock: React.FC<NarrativeBlockProps> = ({
  block,
  onChange,
  editable = true,
  commodity,
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

  /** Append clause text to the textarea (with double newline separator) */
  const handleInsertClause = (clauseText: string) => {
    if (!onChange) return;
    const current = text.trim();
    const newText = current ? `${current}\n\n${clauseText}` : clauseText;
    onChange({
      ...block,
      additional_text: newText,
      surveyor_edited: true,
    });
    // Also move focus to the textarea and push caret to end
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        textareaRef.current.selectionStart = textareaRef.current.value.length;
        textareaRef.current.selectionEnd = textareaRef.current.value.length;
      }
    }, 50);
  };

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
          {/* Clause Library Picker — only shown when editing */}
          <ClauseLibraryPicker
            commodity={commodity}
            sectionHeading={sectionTitle}
            onInsert={handleInsertClause}
          />
          <textarea
            ref={textareaRef}
            value={text}
            onChange={handleTextChange}
            placeholder="Click to enter findings and circumstances, or use Clause Library above…"
            className="w-full bg-transparent border border-transparent hover:border-blue-200 focus:border-blue-500 focus:bg-white focus:outline-none rounded p-1 text-xs leading-relaxed text-slate-800 text-justify font-sans resize-none overflow-hidden transition-colors cursor-text"
          />
        </>
      ) : (
        <div className="space-y-2 text-xs leading-relaxed text-slate-800 text-justify">
          {paragraphs.length > 0 ? (
            paragraphs.map((p: string, idx: number) => (
              <p key={idx}>{renderFormattedText(p)}</p>
            ))
          ) : (
            <p>{renderFormattedText(text)}</p>
          )}
        </div>
      )}
    </div>
  );
};

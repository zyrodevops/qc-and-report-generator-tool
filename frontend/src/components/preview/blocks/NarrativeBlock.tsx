import React, { useRef, useEffect } from 'react';

export interface NarrativeBlockProps {
  block: any;
  onChange?: (updatedBlock: any) => void;
  editable?: boolean;
}

export const NarrativeBlock: React.FC<NarrativeBlockProps> = ({
  block,
  onChange,
  editable = true,
}) => {
  const sectionTitle = block?.section || 'ATTENDANCE & CIRCUMSTANCES';
  const text = block?.additional_text || '';
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.max(60, textareaRef.current.scrollHeight)}px`;
    }
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
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleTextChange}
          placeholder="Click to enter findings and circumstances..."
          className="w-full bg-transparent border border-transparent hover:border-blue-200 focus:border-blue-500 focus:bg-white focus:outline-none rounded p-1 text-xs leading-relaxed text-slate-800 text-justify font-sans resize-none overflow-hidden transition-colors cursor-text"
        />
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

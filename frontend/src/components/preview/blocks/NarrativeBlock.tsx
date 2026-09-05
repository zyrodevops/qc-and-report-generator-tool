import React from 'react';

export interface NarrativeBlockProps {
  block: any;
}

export const NarrativeBlock: React.FC<NarrativeBlockProps> = ({ block }) => {
  const sectionTitle = block?.section || 'ATTENDANCE & CIRCUMSTANCES';
  const text = block?.additional_text || '';

  if (!text && !sectionTitle) return null;

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
      <div className="space-y-2 text-xs leading-relaxed text-slate-800 text-justify">
        {paragraphs.length > 0 ? (
          paragraphs.map((p: string, idx: number) => (
            <p key={idx}>{renderFormattedText(p)}</p>
          ))
        ) : (
          <p>{renderFormattedText(text)}</p>
        )}
      </div>
    </div>
  );
};

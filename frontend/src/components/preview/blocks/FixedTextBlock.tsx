import React from 'react';

export interface FixedTextBlockProps {
  block: any;
  metadata?: any;
}

/**
 * The closing text, exactly as the Word file prints it (render_fixed_text):
 * the block's own lines and nothing else. It used to add a "General
 * Disclaimer & Limitation of Liability" heading, a second Place / Date, and a
 * signature box with a licence number that was not the client's — none of
 * which is in the downloaded report.
 */
export const FixedTextBlock: React.FC<FixedTextBlockProps> = ({ block }) => {
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

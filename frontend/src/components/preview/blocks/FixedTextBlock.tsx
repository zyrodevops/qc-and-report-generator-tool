import React from 'react';

export interface FixedTextBlockProps {
  block: any;
  metadata?: any;
}

export const FixedTextBlock: React.FC<FixedTextBlockProps> = ({
  block,
  metadata,
}) => {
  const content = block?.content || '';
  const place = metadata?.place || 'Mumbai, India';
  const issuedDate = metadata?.issued_date || new Date().toISOString().split('T')[0];

  return (
    <div className="fixed-text-block my-4 pt-2 border-t border-slate-200">
      <div className="bg-slate-50 border border-slate-300 rounded p-3 text-[11px] leading-relaxed text-slate-700 italic">
        <p className="font-bold uppercase tracking-wider text-slate-800 not-italic mb-1 text-[10px]">
          General Disclaimer & Limitation of Liability:
        </p>
        <p>{content}</p>
      </div>

      {/* Surveyor Signature Block */}
      <div className="mt-6 pt-4 border-t border-slate-200 flex justify-between items-end text-xs">
        <div>
          <p className="text-slate-600">
            <span className="font-semibold">Place:</span> {place}
          </p>
          <p className="text-slate-600">
            <span className="font-semibold">Date:</span> {issuedDate}
          </p>
        </div>

        <div className="text-right">
          <p className="font-bold text-[#00387A]">For MARINE CARGO AGENCIES PVT. LTD.</p>
          <div className="h-12 flex items-center justify-end">
            <span className="inline-block border-b border-dashed border-slate-400 w-44"></span>
          </div>
          <p className="text-[11px] font-semibold text-slate-700">Surveyor & Loss Assessor</p>
          <p className="text-[10px] text-slate-500 font-mono">IRDAI SLA Licence No. 12948</p>
        </div>
      </div>
    </div>
  );
};

import React from 'react';

interface AnnexureRow {
  prefix: string;
  title: string;
  sub_id?: string;
}

interface AnnexuresBlockProps {
  block: {
    id: string;
    type: 'annexures';
    rows?: AnnexureRow[];
    _computed?: {
      documentation_list?: string[];
      rows?: AnnexureRow[];
    };
  };
}

export const AnnexuresBlock: React.FC<AnnexuresBlockProps> = ({ block }) => {
  const computedList = block._computed?.documentation_list;
  const rows = block._computed?.rows || block.rows || [];

  const listItems = computedList || rows.map(r => `Annexure ${r.sub_id || r.prefix}: ${r.title}`);

  return (
    <div className="my-4 text-xs font-sans text-gray-800">
      <h2 className="text-[11pt] font-bold text-[#00387A] uppercase border-b border-gray-300 pb-1 mb-2 tracking-wide">
        List of Annexures
      </h2>
      <ul className="list-disc list-inside space-y-1 text-[9pt] text-gray-700 ml-2">
        {listItems.map((item, idx) => (
          <li key={idx} className="leading-snug">{item}</li>
        ))}
      </ul>
    </div>
  );
};

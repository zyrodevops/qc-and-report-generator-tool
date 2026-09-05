import React from 'react';

interface PartiesRow {
  role: string;
  name: string;
  details?: string;
}

interface PartiesBlockProps {
  block: {
    id: string;
    type: 'parties';
    rows?: PartiesRow[];
  };
}

export const PartiesBlock: React.FC<PartiesBlockProps> = ({ block }) => {
  const rows = block.rows || [];
  if (rows.length === 0) return null;

  return (
    <div className="my-4 text-xs font-sans text-gray-800">
      <h2 className="text-[11pt] font-bold text-[#00387A] uppercase border-b border-gray-300 pb-1 mb-2 tracking-wide">
        Parties Involved
      </h2>
      <table className="w-full border-collapse border border-gray-300 text-[9pt]">
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-b border-gray-300">
              <td className="w-[35%] font-bold bg-slate-50 p-1.5 border-r border-gray-300 text-gray-700">
                {r.role}
              </td>
              <td className="p-1.5 text-gray-900">
                {r.name} {r.details && <span className="text-gray-500 font-normal">({r.details})</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

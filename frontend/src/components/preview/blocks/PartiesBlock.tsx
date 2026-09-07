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
  onChange?: (updatedBlock: any) => void;
  editable?: boolean;
}

export const PartiesBlock: React.FC<PartiesBlockProps> = ({
  block,
  onChange,
  editable = true,
}) => {
  const rows = block.rows || [];
  if (rows.length === 0) return null;

  const updateRow = (idx: number, field: keyof PartiesRow, val: string) => {
    if (!onChange) return;
    const newRows = [...rows];
    newRows[idx] = { ...newRows[idx], [field]: val };
    onChange({ ...block, rows: newRows });
  };

  return (
    <div className="my-4 text-xs font-sans text-gray-800">
      <h2 className="text-[11pt] font-bold text-[#00387A] uppercase border-b border-gray-300 pb-1 mb-2 tracking-wide">
        Parties Involved
      </h2>
      <table className="w-full border-collapse border border-gray-300 text-[9pt]">
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-b border-gray-300">
              <td className="w-[35%] font-bold bg-slate-50 p-0 border-r border-gray-300 text-gray-700">
                {editable && onChange ? (
                  <input
                    type="text"
                    value={r.role}
                    onChange={(e) => updateRow(i, 'role', e.target.value)}
                    className="w-full bg-transparent p-1.5 font-bold border-none outline-none hover:bg-blue-50/40 focus:bg-white focus:ring-1 focus:ring-blue-500 text-gray-700 transition-colors"
                  />
                ) : (
                  <div className="p-1.5">{r.role}</div>
                )}
              </td>
              <td className="p-0 text-gray-900">
                {editable && onChange ? (
                  <input
                    type="text"
                    value={r.name}
                    placeholder="Party Name"
                    onChange={(e) => updateRow(i, 'name', e.target.value)}
                    className="w-full bg-transparent p-1.5 border-none outline-none hover:bg-blue-50/40 focus:bg-white focus:ring-1 focus:ring-blue-500 text-gray-900 transition-colors"
                  />
                ) : (
                  <div className="p-1.5">
                    {r.name} {r.details && <span className="text-gray-500 font-normal">({r.details})</span>}
                  </div>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

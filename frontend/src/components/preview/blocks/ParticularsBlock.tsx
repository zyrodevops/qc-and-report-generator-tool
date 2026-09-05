import React from 'react';

export interface ParticularsBlockProps {
  block: any;
  transport?: any;
  carriageUnits?: any[];
  weights?: any;
}

export const ParticularsBlock: React.FC<ParticularsBlockProps> = ({
  block,
}) => {
  const rows: any[] = block?.rows || [];
  if (rows.length === 0) return null;

  const sectionTitle = block.section || 'PARTICULARS OF SURVEY';

  return (
    <div className="particulars-block my-2">
      <h2 className="text-[12px] font-bold text-[#00387A] uppercase tracking-wider border-b border-slate-300 pb-1 mb-2">
        {sectionTitle}
      </h2>
      <table className="w-full border-collapse border border-slate-400 text-xs">
        <tbody>
          {rows.map((row, idx) => {
            const label = row.label || '';
            const rawVal = row.value;
            let valStr = '';

            if (Array.isArray(rawVal)) {
              const parts: string[] = [];
              rawVal.forEach((item) => {
                if (item && typeof item === 'object' && 'amount' in item) {
                  const curr = item.currency || '';
                  parts.push(`${curr} ${item.amount}`.trim());
                } else if (Array.isArray(item)) {
                  parts.push(item.join(', '));
                } else if (item !== undefined && item !== null) {
                  parts.push(String(item));
                }
              });
              valStr = parts.join(', ');
            } else if (rawVal !== undefined && rawVal !== null) {
              valStr = String(rawVal);
            }

            if (row.note) {
              valStr += ` (${row.note})`;
            }

            return (
              <tr key={idx} className="border-b border-slate-300">
                <td className="w-[35%] bg-slate-50 font-semibold text-slate-700 px-3 py-1.5 border-r border-slate-400">
                  {label}
                </td>
                <td className="w-[65%] text-slate-900 px-3 py-1.5 font-sans">
                  {valStr}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

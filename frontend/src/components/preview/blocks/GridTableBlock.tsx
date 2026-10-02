import React from 'react';
import type { GridTable } from '../../../utils/gcTables';

/** A general cargo table as Word prints it: bold header, the total row bold. */
export const GridTableBlock: React.FC<{ table: GridTable | null; testId?: string }> = ({ table, testId }) => {
  if (!table || !table.rows.length) return null;
  return (
    <div className="my-2" data-testid={testId}>
      {table.title && (
        <h2 className="text-[12px] font-bold text-[#00387A] uppercase tracking-wider border-b border-slate-300 pb-1 mb-2">
          {table.title}
        </h2>
      )}
      <table className="w-full border-collapse text-[9pt]">
        <thead>
          <tr>
            {table.columns.map((h) => (
              <th key={h} className="border border-slate-400 px-1.5 py-0.5 text-left font-bold bg-slate-50">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((r, i) => (
            <tr key={i} className={table.total && i === table.rows.length - 1 ? 'font-bold' : ''}>
              {r.map((v, j) => (
                <td key={j} className="border border-slate-400 px-1.5 py-0.5">{v}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default GridTableBlock;

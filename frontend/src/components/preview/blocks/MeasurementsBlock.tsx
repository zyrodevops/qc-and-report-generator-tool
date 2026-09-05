import React from 'react';

export interface MeasurementsBlockProps {
  block: any;
}

export const MeasurementsBlock: React.FC<MeasurementsBlockProps> = ({ block }) => {
  const rows: any[] = block?.rows || [];
  if (rows.length === 0) return null;

  return (
    <div className="measurements-block my-2">
      <h2 className="text-[12px] font-bold text-[#00387A] uppercase tracking-wider border-b border-slate-300 pb-1 mb-2">
        MEASUREMENTS & SENSORY CHECKS
      </h2>
      <table className="w-full border-collapse border border-slate-400 text-xs">
        <thead>
          <tr className="bg-slate-100 text-slate-800 font-bold border-b border-slate-400">
            <th className="border border-slate-400 px-2.5 py-1.5 text-left">Subject</th>
            <th className="border border-slate-400 px-2.5 py-1.5 text-left">Qualifier</th>
            <th className="border border-slate-400 px-2.5 py-1.5 text-left">Method</th>
            <th className="border border-slate-400 px-2.5 py-1.5 text-left">Min / Value</th>
            <th className="border border-slate-400 px-2.5 py-1.5 text-left">Max / Unit</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => {
            const subj = row.subject || '';
            const qual = row.qualifier || '';
            const meth = row.method || '';
            const minV = row.min ?? row.value ?? '';
            const maxV = row.max ?? '';
            const unit = row.unit || '';
            const maxUnit = maxV ? `${maxV} ${unit}`.trim() : unit;

            return (
              <tr key={idx} className="border-b border-slate-300">
                <td className="border border-slate-400 px-2.5 py-1.5 font-medium text-slate-800">
                  {subj}
                </td>
                <td className="border border-slate-400 px-2.5 py-1.5 text-slate-600">
                  {qual}
                </td>
                <td className="border border-slate-400 px-2.5 py-1.5 text-slate-600">
                  {meth}
                </td>
                <td className="border border-slate-400 px-2.5 py-1.5 font-mono text-slate-800">
                  {String(minV)}
                </td>
                <td className="border border-slate-400 px-2.5 py-1.5 font-mono text-slate-800">
                  {maxUnit}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

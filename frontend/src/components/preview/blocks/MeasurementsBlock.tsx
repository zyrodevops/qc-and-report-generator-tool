import React from 'react';

export interface MeasurementsBlockProps {
  block: any;
  onChange?: (updatedBlock: any) => void;
  editable?: boolean;
}

export const MeasurementsBlock: React.FC<MeasurementsBlockProps> = ({
  block,
  onChange,
  editable = true,
}) => {
  const rows: any[] = block?.rows || [];
  if (!rows.some((r) => r?.included !== false)) return null;

  const updateRow = (rIdx: number, field: string, val: string) => {
    if (!onChange) return;
    const newRows = [...rows];
    newRows[rIdx] = { ...newRows[rIdx], [field]: val };
    onChange({ ...block, rows: newRows });
  };

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
            if (row?.included === false) return null;
            const subj = row.subject || '';
            const qual = row.qualifier || '';
            const meth = row.method || '';
            const minV = row.min ?? row.value ?? '';
            const maxV = row.max ?? '';
            const unit = row.unit || '';
            const maxUnit = maxV ? `${maxV} ${unit}`.trim() : unit;

            return (
              <tr key={idx} className="border-b border-slate-300">
                <td className="border border-slate-400 p-0 font-medium text-slate-800">
                  {editable && onChange ? (
                    <input
                      type="text"
                      value={subj}
                      onChange={(e) => updateRow(idx, 'subject', e.target.value)}
                      className="w-full bg-transparent px-2.5 py-1.5 border-none outline-none hover:bg-blue-50/40 focus:bg-white focus:ring-1 focus:ring-blue-500 text-xs text-slate-800 transition-colors"
                    />
                  ) : (
                    <div className="px-2.5 py-1.5">{subj}</div>
                  )}
                </td>
                <td className="border border-slate-400 p-0 text-slate-600">
                  {editable && onChange ? (
                    <input
                      type="text"
                      value={qual}
                      onChange={(e) => updateRow(idx, 'qualifier', e.target.value)}
                      className="w-full bg-transparent px-2.5 py-1.5 border-none outline-none hover:bg-blue-50/40 focus:bg-white focus:ring-1 focus:ring-blue-500 text-xs text-slate-600 transition-colors"
                    />
                  ) : (
                    <div className="px-2.5 py-1.5">{qual}</div>
                  )}
                </td>
                <td className="border border-slate-400 p-0 text-slate-600">
                  {editable && onChange ? (
                    <input
                      type="text"
                      value={meth}
                      onChange={(e) => updateRow(idx, 'method', e.target.value)}
                      className="w-full bg-transparent px-2.5 py-1.5 border-none outline-none hover:bg-blue-50/40 focus:bg-white focus:ring-1 focus:ring-blue-500 text-xs text-slate-600 transition-colors"
                    />
                  ) : (
                    <div className="px-2.5 py-1.5">{meth}</div>
                  )}
                </td>
                <td className="border border-slate-400 p-0 font-mono text-slate-800">
                  {editable && onChange ? (
                    <input
                      type="text"
                      value={String(minV)}
                      onChange={(e) => {
                        const valKey = row.min !== undefined ? 'min' : 'value';
                        updateRow(idx, valKey, e.target.value);
                      }}
                      className="w-full bg-transparent px-2.5 py-1.5 border-none outline-none hover:bg-blue-50/40 focus:bg-white focus:ring-1 focus:ring-blue-500 text-xs font-mono text-slate-800 transition-colors"
                    />
                  ) : (
                    <div className="px-2.5 py-1.5 font-mono">{String(minV)}</div>
                  )}
                </td>
                <td className="border border-slate-400 p-0 font-mono text-slate-800">
                  {editable && onChange ? (
                    <div className="flex items-center">
                      <input
                        type="text"
                        value={String(maxV)}
                        placeholder="Max"
                        onChange={(e) => updateRow(idx, 'max', e.target.value)}
                        className="w-16 bg-transparent px-2.5 py-1.5 border-none outline-none hover:bg-blue-50/40 focus:bg-white focus:ring-1 focus:ring-blue-500 text-xs font-mono text-slate-800 transition-colors"
                      />
                      <input
                        type="text"
                        value={unit}
                        placeholder="Unit"
                        onChange={(e) => updateRow(idx, 'unit', e.target.value)}
                        className="w-16 bg-transparent px-1 py-1.5 border-none outline-none hover:bg-blue-50/40 focus:bg-white focus:ring-1 focus:ring-blue-500 text-xs font-mono text-slate-600 transition-colors"
                      />
                    </div>
                  ) : (
                    <div className="px-2.5 py-1.5 font-mono">{maxUnit}</div>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

import React from 'react';

interface ReconciliationRow {
  subject: string;
  gross?: string;
  container_tare?: string;
  trailer_tare?: string;
  found_net?: string;
  reference?: string;
  difference?: string;
  direction?: string;
}

interface ReconciliationBlockProps {
  block: {
    id: string;
    type: 'reconciliation';
    title?: string;
    rows?: ReconciliationRow[];
    _computed?: {
      rows?: ReconciliationRow[];
      total_gross?: string;
      total_found_net?: string;
      total_reference?: string;
      total_difference?: string;
      direction?: string;
      summary?: string;
    };
  };
}

export const ReconciliationBlock: React.FC<ReconciliationBlockProps> = ({ block }) => {
  const computed = block._computed || {};
  const rows = computed.rows || block.rows || [];
  const title = block.title || 'Weight Reconciliation';

  if (rows.length === 0) return null;

  const totalGross = computed.total_gross || '-';
  const totalFoundNet = computed.total_found_net || '-';
  const totalRef = computed.total_reference || '-';
  let totalDiff = computed.total_difference || '0';
  if (computed.direction && computed.direction !== 'NIL') {
    totalDiff += ' (' + computed.direction + ')';
  }

  return (
    <div className="my-4 text-xs font-sans text-gray-800">
      <h2 className="text-[11pt] font-bold text-[#00387A] uppercase border-b border-gray-300 pb-1 mb-2 tracking-wide">
        {title}
      </h2>
      <table className="w-full border-collapse border border-gray-400 text-[9pt]">
        <thead>
          <tr className="border-b border-gray-400 bg-white">
            <th className="p-1.5 border border-gray-400 text-left font-bold text-gray-900">Container / Item</th>
            <th className="p-1.5 border border-gray-400 text-right font-bold text-gray-900">Gross Wt (kg)</th>
            <th className="p-1.5 border border-gray-400 text-right font-bold text-gray-900">Tare (kg)</th>
            <th className="p-1.5 border border-gray-400 text-right font-bold text-gray-900">Found Net (kg)</th>
            <th className="p-1.5 border border-gray-400 text-right font-bold text-gray-900">Declared (kg)</th>
            <th className="p-1.5 border border-gray-400 text-right font-bold text-gray-900">Difference (kg)</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const tare = r.container_tare || r.trailer_tare || '-';
            let diffStr = r.difference || '0';
            if (r.direction && r.direction !== 'NIL') {
              diffStr += ' (' + r.direction + ')';
            }
            return (
              <tr key={i} className="border-b border-gray-400 hover:bg-slate-50/50">
                <td className="p-1.5 border border-gray-400 font-medium text-gray-900">{r.subject}</td>
                <td className="p-1.5 border border-gray-400 text-right text-gray-800">{r.gross || '-'}</td>
                <td className="p-1.5 border border-gray-400 text-right text-gray-800">{tare}</td>
                <td className="p-1.5 border border-gray-400 text-right font-medium text-gray-900">{r.found_net || '-'}</td>
                <td className="p-1.5 border border-gray-400 text-right text-gray-800">{r.reference || '-'}</td>
                <td className="p-1.5 border border-gray-400 text-right font-bold text-gray-900">{diffStr}</td>
              </tr>
            );
          })}
          <tr className="bg-slate-100 font-bold border-t-2 border-gray-400 text-gray-900">
            <td className="p-1.5 border-r border-gray-300">TOTAL / SUMMARY</td>
            <td className="p-1.5 border-r border-gray-300 text-right">{totalGross}</td>
            <td className="p-1.5 border-r border-gray-300 text-right">-</td>
            <td className="p-1.5 border-r border-gray-300 text-right">{totalFoundNet}</td>
            <td className="p-1.5 border-r border-gray-300 text-right">{totalRef}</td>
            <td className="p-1.5 border-gray-300 text-right">{totalDiff}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
};

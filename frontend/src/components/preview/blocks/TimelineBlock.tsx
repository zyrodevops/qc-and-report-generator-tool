import React from 'react';

interface TimelineRow {
  event: string;
  date: string;
  location?: string;
  basis?: string;
}

interface TimelineBlockProps {
  block: {
    id: string;
    type: 'timeline';
    rows?: TimelineRow[];
    _computed?: {
      transit_days?: number;
    };
  };
  onChange?: (updatedBlock: any) => void;
  editable?: boolean;
}

export const TimelineBlock: React.FC<TimelineBlockProps> = ({
  block,
  onChange,
  editable = true,
}) => {
  const rows = block.rows || [];
  const transitDays = block._computed?.transit_days;

  const updateRow = (idx: number, field: keyof TimelineRow, val: string) => {
    if (!onChange) return;
    const newRows = [...rows];
    newRows[idx] = { ...newRows[idx], [field]: val };
    onChange({ ...block, rows: newRows });
  };

  return (
    <div className="my-4 text-xs font-sans text-gray-800">
      <h2 className="text-[11pt] font-bold text-[#00387A] uppercase border-b border-gray-300 pb-1 mb-2 tracking-wide">
        Shipment & Survey Timeline
      </h2>
      {rows.length > 0 && (
        <table className="w-full border-collapse border border-gray-300 text-[9pt]">
          <thead>
            <tr className="bg-[#00387A] text-white font-bold">
              <th className="p-1.5 border border-gray-300 text-left">Event</th>
              <th className="p-1.5 border border-gray-300 text-left">Date</th>
              <th className="p-1.5 border border-gray-300 text-left">Location</th>
              <th className="p-1.5 border border-gray-300 text-left">Basis</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-b border-gray-300 hover:bg-slate-50">
                <td className="p-0 border-r border-gray-300 font-semibold text-gray-900">
                  {editable && onChange ? (
                    <input
                      type="text"
                      value={r.event}
                      onChange={(e) => updateRow(i, 'event', e.target.value)}
                      className="w-full bg-transparent p-1.5 font-semibold border-none outline-none hover:bg-blue-50/40 focus:bg-white focus:ring-1 focus:ring-blue-500 text-gray-900 transition-colors"
                    />
                  ) : (
                    <div className="p-1.5">{r.event}</div>
                  )}
                </td>
                <td className="p-0 border-r border-gray-300 text-gray-700">
                  {editable && onChange ? (
                    <input
                      type="text"
                      value={r.date}
                      placeholder="YYYY-MM-DD"
                      onChange={(e) => updateRow(i, 'date', e.target.value)}
                      className="w-full bg-transparent p-1.5 border-none outline-none hover:bg-blue-50/40 focus:bg-white focus:ring-1 focus:ring-blue-500 text-gray-700 transition-colors"
                    />
                  ) : (
                    <div className="p-1.5">{r.date}</div>
                  )}
                </td>
                <td className="p-0 border-r border-gray-300 text-gray-700">
                  {editable && onChange ? (
                    <input
                      type="text"
                      value={r.location || ''}
                      placeholder="Location"
                      onChange={(e) => updateRow(i, 'location', e.target.value)}
                      className="w-full bg-transparent p-1.5 border-none outline-none hover:bg-blue-50/40 focus:bg-white focus:ring-1 focus:ring-blue-500 text-gray-700 transition-colors"
                    />
                  ) : (
                    <div className="p-1.5">{r.location || '-'}</div>
                  )}
                </td>
                <td className="p-0 border-gray-300 text-gray-700">
                  {editable && onChange ? (
                    <input
                      type="text"
                      value={r.basis || ''}
                      placeholder="Basis"
                      onChange={(e) => updateRow(i, 'basis', e.target.value)}
                      className="w-full bg-transparent p-1.5 border-none outline-none hover:bg-blue-50/40 focus:bg-white focus:ring-1 focus:ring-blue-500 text-gray-700 transition-colors"
                    />
                  ) : (
                    <div className="p-1.5">{r.basis || 'as reported'}</div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {transitDays !== undefined && (
        <p className="mt-1 text-[8.5pt] italic text-slate-600">
          Total Transit Duration: {transitDays} day(s)
        </p>
      )}
    </div>
  );
};

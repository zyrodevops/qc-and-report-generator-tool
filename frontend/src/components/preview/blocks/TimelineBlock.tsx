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
}

export const TimelineBlock: React.FC<TimelineBlockProps> = ({ block }) => {
  const rows = block.rows || [];
  const transitDays = block._computed?.transit_days;

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
                <td className="p-1.5 border-r border-gray-300 font-semibold text-gray-900">{r.event}</td>
                <td className="p-1.5 border-r border-gray-300 text-gray-700">{r.date}</td>
                <td className="p-1.5 border-r border-gray-300 text-gray-700">{r.location || '-'}</td>
                <td className="p-1.5 border-gray-300 text-gray-700">{r.basis || 'as reported'}</td>
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

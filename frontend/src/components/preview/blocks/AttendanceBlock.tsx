import React from 'react';

interface AttendanceRow {
  name: string;
  designation: string;
  representing: string;
}

interface AttendanceBlockProps {
  block: {
    id: string;
    type: 'attendance';
    rows?: AttendanceRow[];
  };
}

export const AttendanceBlock: React.FC<AttendanceBlockProps> = ({ block }) => {
  const rows = block.rows || [];
  if (rows.length === 0) return null;

  return (
    <div className="my-4 text-xs font-sans text-gray-800">
      <h2 className="text-[11pt] font-bold text-[#00387A] uppercase border-b border-gray-300 pb-1 mb-2 tracking-wide">
        Attendance at Survey
      </h2>
      <table className="w-full border-collapse border border-gray-300 text-[9pt]">
        <thead>
          <tr className="bg-[#00387A] text-white font-bold">
            <th className="p-1.5 border border-gray-300 text-left">Name</th>
            <th className="p-1.5 border border-gray-300 text-left">Designation</th>
            <th className="p-1.5 border border-gray-300 text-left">Representing</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-b border-gray-300 hover:bg-slate-50">
              <td className="p-1.5 border-r border-gray-300 font-medium text-gray-900">{r.name}</td>
              <td className="p-1.5 border-r border-gray-300 text-gray-700">{r.designation}</td>
              <td className="p-1.5 border-gray-300 text-gray-700">{r.representing}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

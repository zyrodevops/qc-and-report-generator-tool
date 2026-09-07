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
  onChange?: (updatedBlock: any) => void;
  editable?: boolean;
}

export const AttendanceBlock: React.FC<AttendanceBlockProps> = ({
  block,
  onChange,
  editable = true,
}) => {
  const rows = block.rows || [];
  if (rows.length === 0) return null;

  const updateRow = (idx: number, field: keyof AttendanceRow, val: string) => {
    if (!onChange) return;
    const newRows = [...rows];
    newRows[idx] = { ...newRows[idx], [field]: val };
    onChange({ ...block, rows: newRows });
  };

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
              <td className="p-0 border-r border-gray-300 font-medium text-gray-900">
                {editable && onChange ? (
                  <input
                    type="text"
                    value={r.name}
                    placeholder="Attendee Name"
                    onChange={(e) => updateRow(i, 'name', e.target.value)}
                    className="w-full bg-transparent p-1.5 font-medium border-none outline-none hover:bg-blue-50/40 focus:bg-white focus:ring-1 focus:ring-blue-500 text-gray-900 transition-colors"
                  />
                ) : (
                  <div className="p-1.5">{r.name}</div>
                )}
              </td>
              <td className="p-0 border-r border-gray-300 text-gray-700">
                {editable && onChange ? (
                  <input
                    type="text"
                    value={r.designation}
                    placeholder="Designation"
                    onChange={(e) => updateRow(i, 'designation', e.target.value)}
                    className="w-full bg-transparent p-1.5 border-none outline-none hover:bg-blue-50/40 focus:bg-white focus:ring-1 focus:ring-blue-500 text-gray-700 transition-colors"
                  />
                ) : (
                  <div className="p-1.5">{r.designation}</div>
                )}
              </td>
              <td className="p-0 border-gray-300 text-gray-700">
                {editable && onChange ? (
                  <input
                    type="text"
                    value={r.representing}
                    placeholder="Representing"
                    onChange={(e) => updateRow(i, 'representing', e.target.value)}
                    className="w-full bg-transparent p-1.5 border-none outline-none hover:bg-blue-50/40 focus:bg-white focus:ring-1 focus:ring-blue-500 text-gray-700 transition-colors"
                  />
                ) : (
                  <div className="p-1.5">{r.representing}</div>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

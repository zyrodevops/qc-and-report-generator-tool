import React from 'react';
import { Plus, Trash2, Users } from 'lucide-react';

interface Props {
  rows: any[];
  intro: string;
  onChange: (rows: any[], intro: string) => void;
  /** Heading shown above the editor. */
  label?: string;
}

const FIELDS: { key: 'name' | 'designation' | 'representing'; label: string; width: string }[] = [
  { key: 'name', label: 'Name', width: 'w-48' },
  { key: 'designation', label: 'Designation', width: 'w-44' },
  { key: 'representing', label: 'Representing', width: 'flex-1' },
];

/** Who attended the survey: the client's Name / Designation / Representing table. */
export const AttendanceEditor: React.FC<Props> = ({ rows, intro, onChange, label = 'Attendance' }) => {
  const set = (i: number, key: string, v: string) => {
    const next = [...rows];
    next[i] = { ...next[i], [key]: v };
    onChange(next, intro);
  };
  return (
    <div className="space-y-2" data-testid="attendance-editor">
      <div className="flex items-center gap-2 text-sm font-semibold text-gray-700">
        <Users className="w-4 h-4 text-blue-600" />
        {label}
        <span className="text-xs font-normal text-gray-400">({rows.length} {rows.length === 1 ? 'person' : 'people'})</span>
      </div>
      <input
        value={intro}
        aria-label="Line above the attendance table"
        onChange={(e) => onChange(rows, e.target.value)}
        className="w-full px-2 py-1 border border-gray-200 rounded text-xs text-gray-600 outline-none focus:ring-1 focus:ring-blue-500"
      />
      {rows.map((r, i) => (
        <div key={i} className="flex items-center gap-2">
          {FIELDS.map((f) => (
            <input
              key={f.key}
              value={r[f.key] || ''}
              placeholder={f.label}
              aria-label={`${f.label} ${i + 1}`}
              onChange={(e) => set(i, f.key, e.target.value)}
              className={`${f.width} px-2 py-1.5 border border-gray-300 rounded text-sm outline-none focus:ring-1 focus:ring-blue-500`}
            />
          ))}
          <button
            type="button"
            onClick={() => onChange(rows.filter((_, j) => j !== i), intro)}
            className="p-1 text-gray-300 hover:text-red-500"
            aria-label={`Remove person ${i + 1}`}
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={() => onChange([...rows, { name: '', designation: '', representing: '' }], intro)}
        className="flex items-center gap-1 text-xs text-blue-700 font-medium hover:underline"
      >
        <Plus className="w-3.5 h-3.5" /> Add a person
      </button>
    </div>
  );
};

export default AttendanceEditor;

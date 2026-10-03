import React, { useState, useEffect, useRef } from 'react';
import {
  Users,
  Plus,
  Trash2,
  ChevronDown,
  Sparkles,
  Ship,
  Check,
  ShieldCheck,
  Package,
} from 'lucide-react';
import {
  Attendee,
  staffData,
  lookupConsigneeStaff,
  suggestShippingLineSurveyors,
  getDefaultAttendance,
} from '../../utils/staffLookup';

interface ApplicationAttendanceProps {
  rows: Attendee[];
  intro?: string;
  consigneeName?: string;
  vesselName?: string;
  editable?: boolean;
  isFormEditor?: boolean;
  onChange: (rows: Attendee[], intro: string) => void;
}

export const ApplicationAttendance: React.FC<ApplicationAttendanceProps> = ({
  rows = [],
  intro = 'The following persons attended the survey:',
  consigneeName = '',
  vesselName = '',
  editable = true,
  isFormEditor = true,
  onChange,
}) => {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [activeCategory, setActiveCategory] = useState<'shipping' | 'shipper' | 'insurer' | 'mca'>('shipping');
  const dropdownRef = useRef<HTMLDivElement | null>(null);

  const isJoint = intro.toLowerCase().includes('joint');

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    if (dropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [dropdownOpen]);

  // Check if consignee staff is matched but not yet in the table
  const matchedConsigneeStaff = lookupConsigneeStaff(consigneeName);
  const hasMatchedConsigneeStaff =
    matchedConsigneeStaff.length > 0 &&
    matchedConsigneeStaff.every((cs) =>
      rows.some((r) => r.name.trim().toLowerCase() === cs.name.trim().toLowerCase())
    );
  const missingConsigneeStaff = matchedConsigneeStaff.filter(
    (cs) => !rows.some((r) => r.name.trim().toLowerCase() === cs.name.trim().toLowerCase())
  );

  // Suggested shipping line surveyors based on vessel
  const suggestedLineSurveyors = suggestShippingLineSurveyors(vesselName).filter(
    (sl) => !rows.some((r) => r.name.trim().toLowerCase() === sl.name.trim().toLowerCase())
  );

  const handleToggleJoint = (joint: boolean) => {
    if (!onChange) return;
    const newIntro = joint
      ? 'The following persons attended the joint survey:'
      : 'The following persons attended the survey:';
    onChange(rows, newIntro);
  };

  const handleUpdateRow = (index: number, field: keyof Attendee, value: string) => {
    if (!onChange) return;
    const next = [...rows];
    next[index] = { ...next[index], [field]: value };
    onChange(next, intro);
  };

  const handleDeleteRow = (index: number) => {
    if (!onChange) return;
    const next = rows.filter((_, i) => i !== index);
    onChange(next, intro);
  };

  const handleAddBlankRow = () => {
    if (!onChange) return;
    onChange([...rows, { name: '', designation: '', representing: '' }], intro);
  };

  const handleAddAttendee = (attendee: Attendee) => {
    if (!onChange) return;
    // Don't add duplicate
    if (rows.some((r) => r.name.trim().toLowerCase() === attendee.name.trim().toLowerCase())) {
      setDropdownOpen(false);
      return;
    }
    onChange([...rows, { ...attendee }], intro);
    setDropdownOpen(false);
  };

  const handleAutoFillConsignee = () => {
    if (!onChange || matchedConsigneeStaff.length === 0) return;
    // Keep MCA surveyor and any joint surveyors, replace previous consignee rows
    const nonConsigneeRows = rows.filter((r) => {
      const rep = (r.representing || '').toLowerCase();
      const isMCA = rep.includes('marine cargo agencies') || r.name.toLowerCase().includes('baburao');
      const isLineOrShipper =
        rep.includes('shipping line') ||
        rep.includes('shipper') ||
        rep.includes('insurer') ||
        rep.includes('underwriter') ||
        rep.includes('wan hai') ||
        rep.includes('oocl');
      return isMCA || isLineOrShipper;
    });
    if (!nonConsigneeRows.some((r) => (r.representing || '').toLowerCase().includes('marine cargo agencies') || r.name.toLowerCase().includes('baburao'))) {
      nonConsigneeRows.push({
        name: 'Mr. Baburao Bhosale',
        designation: 'Surveyor',
        representing: 'Marine Cargo Agencies Pvt.Ltd (On behalf of Consignees)',
      });
    }
    onChange([...matchedConsigneeStaff, ...nonConsigneeRows], intro);
  };

  // ── A4 HTML PREVIEW MODE: Pure, clean document table with direct in-place editing ──
  if (!isFormEditor) {
    if (rows.length === 0) return null;
    return (
      <div className="my-3 text-xs font-sans text-gray-800" data-testid="a4-attendance-table">
        <div className="mb-1.5">
          {editable ? (
            <input
              type="text"
              value={intro}
              onChange={(e) => onChange(rows, e.target.value)}
              className="w-full text-xs text-slate-800 bg-transparent border-none outline-none hover:bg-blue-50/40 focus:bg-white focus:ring-1 focus:ring-blue-500 font-medium p-0.5 rounded transition-colors"
            />
          ) : (
            <p className="text-xs text-slate-800 font-medium">{intro}</p>
          )}
        </div>
        <table className="w-full border-collapse border border-gray-400 text-[9pt]">
          <thead>
            <tr className="border-b border-gray-400 bg-white">
              <th className="p-1.5 border border-gray-400 text-left font-bold text-gray-900 w-[30%]">Name</th>
              <th className="p-1.5 border border-gray-400 text-left font-bold text-gray-900 w-[25%]">Designation</th>
              <th className="p-1.5 border border-gray-400 text-left font-bold text-gray-900">Representing</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr key={idx} className="border-b border-gray-400 hover:bg-slate-50/50">
                <td className="p-0 border border-gray-400 font-medium text-gray-900">
                  {editable ? (
                    <input
                      type="text"
                      value={row.name}
                      placeholder="Attendee Name"
                      onChange={(e) => handleUpdateRow(idx, 'name', e.target.value)}
                      className="w-full bg-transparent p-1.5 font-medium border-none outline-none hover:bg-blue-50/40 focus:bg-white focus:ring-1 focus:ring-blue-500 text-gray-900 transition-colors"
                    />
                  ) : (
                    <div className="p-1.5">{row.name}</div>
                  )}
                </td>
                <td className="p-0 border border-gray-400 text-gray-800">
                  {editable ? (
                    <input
                      type="text"
                      value={row.designation}
                      placeholder="Designation"
                      onChange={(e) => handleUpdateRow(idx, 'designation', e.target.value)}
                      className="w-full bg-transparent p-1.5 border-none outline-none hover:bg-blue-50/40 focus:bg-white focus:ring-1 focus:ring-blue-500 text-gray-800 transition-colors"
                    />
                  ) : (
                    <div className="p-1.5">{row.designation}</div>
                  )}
                </td>
                <td className="p-0 border border-gray-400 text-gray-800">
                  {editable ? (
                    <input
                      type="text"
                      value={row.representing}
                      placeholder="Representing"
                      onChange={(e) => handleUpdateRow(idx, 'representing', e.target.value)}
                      className="w-full bg-transparent p-1.5 border-none outline-none hover:bg-blue-50/40 focus:bg-white focus:ring-1 focus:ring-blue-500 text-gray-800 transition-colors"
                    />
                  ) : (
                    <div className="p-1.5">{row.representing}</div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div className="mt-4 pt-3 border-t border-slate-200" data-testid="application-attendance-section">
      {/* HEADER BAR */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-[#00387A]" />
          <span className="text-xs font-bold text-slate-800 tracking-wide uppercase">
            Attendance at Survey
          </span>
          <span className="text-[11px] text-slate-400">
            ({rows.length} {rows.length === 1 ? 'person' : 'persons'})
          </span>
        </div>

        {editable && (
          <label className="flex items-center gap-1.5 cursor-pointer text-xs font-medium text-slate-700 select-none bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded px-2.5 py-1 transition-colors">
            <input
              type="checkbox"
              checked={isJoint}
              onChange={(e) => handleToggleJoint(e.target.checked)}
              className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 w-3.5 h-3.5"
            />
            <span>Joint Survey</span>
          </label>
        )}
      </div>

      {/* INTRO SENTENCE */}
      {editable ? (
        <div className="mb-2">
          <input
            type="text"
            value={intro}
            onChange={(e) => onChange(rows, e.target.value)}
            className="w-full text-xs text-slate-700 bg-transparent border-b border-dashed border-slate-300 hover:border-slate-400 focus:border-blue-500 focus:bg-white focus:outline-none py-1 transition-colors font-medium"
            placeholder="The following persons attended the survey:"
          />
        </div>
      ) : (
        <p className="text-xs text-slate-700 mb-2 font-medium">{intro}</p>
      )}

      {/* AUTO-FILL SUGGESTION BANNERS */}
      {editable && missingConsigneeStaff.length > 0 && (
        <div className="mb-3 p-2 bg-blue-50/70 border border-blue-200 rounded-lg flex items-center justify-between gap-3 text-xs text-blue-900 animate-fadeIn">
          <div className="flex items-center gap-2">
            <Sparkles className="w-3.5 h-3.5 text-blue-600 shrink-0" />
            <span>
              Consignee <strong>{consigneeName}</strong> staff identified:{' '}
              {missingConsigneeStaff.map((s) => `${s.name} (${s.designation})`).join(', ')}
            </span>
          </div>
          <button
            type="button"
            onClick={handleAutoFillConsignee}
            className="shrink-0 px-2.5 py-1 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded text-[11px] shadow-sm transition-colors"
          >
            + Auto-fill
          </button>
        </div>
      )}

      {editable && suggestedLineSurveyors.length > 0 && (
        <div className="mb-3 p-2 bg-amber-50/70 border border-amber-200 rounded-lg flex items-center justify-between gap-3 text-xs text-amber-900 animate-fadeIn">
          <div className="flex items-center gap-2">
            <Ship className="w-3.5 h-3.5 text-amber-600 shrink-0" />
            <span>
              Vessel carries <strong>{suggestedLineSurveyors[0].line}</strong>: Suggest{' '}
              {suggestedLineSurveyors[0].name} ({suggestedLineSurveyors[0].representing})
            </span>
          </div>
          <button
            type="button"
            onClick={() => handleAddAttendee(suggestedLineSurveyors[0])}
            className="shrink-0 px-2.5 py-1 bg-amber-600 hover:bg-amber-700 text-white font-medium rounded text-[11px] shadow-sm transition-colors"
          >
            + Add Line Surveyor
          </button>
        </div>
      )}

      {/* 3-COLUMN ATTENDANCE TABLE */}
      <div className="border border-slate-300 rounded overflow-hidden shadow-sm mb-3">
        <table className="w-full border-collapse text-xs">
          <thead>
            <tr className="bg-[#00387A] text-white font-semibold text-left">
              <th className="p-2 border-r border-[#1a4a88] w-[30%]">Name</th>
              <th className="p-2 border-r border-[#1a4a88] w-[25%]">Designation</th>
              <th className="p-2 border-r border-[#1a4a88]">Representing</th>
              {editable && <th className="p-2 w-10 text-center"></th>}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={editable ? 4 : 3} className="p-4 text-center text-slate-400 italic">
                  No attendance records added yet. Click "+ Add Joint Surveyor" or "+ Add Person" below.
                </td>
              </tr>
            ) : (
              rows.map((row, idx) => (
                <tr key={idx} className="border-b border-slate-200 hover:bg-slate-50 transition-colors">
                  <td className="p-1 border-r border-slate-200">
                    {editable ? (
                      <input
                        type="text"
                        value={row.name}
                        onChange={(e) => handleUpdateRow(idx, 'name', e.target.value)}
                        placeholder="e.g. Mr. Rajendra Ambre"
                        className="w-full p-1 bg-transparent border-none outline-none focus:bg-white focus:ring-1 focus:ring-blue-500 rounded font-medium text-slate-900"
                      />
                    ) : (
                      <span className="p-1 font-medium text-slate-900 block">{row.name}</span>
                    )}
                  </td>
                  <td className="p-1 border-r border-slate-200">
                    {editable ? (
                      <input
                        type="text"
                        value={row.designation}
                        onChange={(e) => handleUpdateRow(idx, 'designation', e.target.value)}
                        placeholder="e.g. Sales Manager"
                        className="w-full p-1 bg-transparent border-none outline-none focus:bg-white focus:ring-1 focus:ring-blue-500 rounded text-slate-700"
                      />
                    ) : (
                      <span className="p-1 text-slate-700 block">{row.designation}</span>
                    )}
                  </td>
                  <td className="p-1 border-r border-slate-200">
                    {editable ? (
                      <input
                        type="text"
                        value={row.representing}
                        onChange={(e) => handleUpdateRow(idx, 'representing', e.target.value)}
                        placeholder="e.g. Hari Agro Products - (Consignees)"
                        className="w-full p-1 bg-transparent border-none outline-none focus:bg-white focus:ring-1 focus:ring-blue-500 rounded text-slate-700"
                      />
                    ) : (
                      <span className="p-1 text-slate-700 block">{row.representing}</span>
                    )}
                  </td>
                  {editable && (
                    <td className="p-1 text-center">
                      <button
                        type="button"
                        onClick={() => handleDeleteRow(idx)}
                        className="p-1 text-slate-400 hover:text-red-600 rounded transition-colors"
                        title="Remove attendee"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* ACTION BUTTONS & DROPDOWN */}
      {editable && (
        <div className="flex flex-wrap items-center gap-2 relative" ref={dropdownRef}>
          {/* Quick-add Joint Surveyor Dropdown */}
          <button
            type="button"
            onClick={() => setDropdownOpen((prev) => !prev)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#00387A] hover:bg-[#002855] text-white text-xs font-semibold rounded shadow-sm transition-colors"
          >
            <span>+ Add Joint Surveyor</span>
            <ChevronDown className="w-3.5 h-3.5" />
          </button>

          {/* Add blank person row */}
          <button
            type="button"
            onClick={handleAddBlankRow}
            className="flex items-center gap-1 px-3 py-1.5 bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 text-xs font-medium rounded shadow-sm transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Custom Person</span>
          </button>

          {/* DROPDOWN MENU */}
          {dropdownOpen && (
            <div className="absolute top-full left-0 mt-1 w-96 max-w-[90vw] bg-white border border-slate-200 rounded-xl shadow-xl z-50 overflow-hidden text-xs animate-fadeIn">
              {/* Category tabs */}
              <div className="flex border-b border-slate-200 bg-slate-50">
                <button
                  type="button"
                  onClick={() => setActiveCategory('shipping')}
                  className={`flex-1 py-2 text-center font-semibold border-b-2 transition-colors ${
                    activeCategory === 'shipping'
                      ? 'border-[#00387A] text-[#00387A] bg-white'
                      : 'border-transparent text-slate-500 hover:text-slate-800'
                  }`}
                >
                  Shipping Line
                </button>
                <button
                  type="button"
                  onClick={() => setActiveCategory('shipper')}
                  className={`flex-1 py-2 text-center font-semibold border-b-2 transition-colors ${
                    activeCategory === 'shipper'
                      ? 'border-[#00387A] text-[#00387A] bg-white'
                      : 'border-transparent text-slate-500 hover:text-slate-800'
                  }`}
                >
                  Shipper
                </button>
                <button
                  type="button"
                  onClick={() => setActiveCategory('insurer')}
                  className={`flex-1 py-2 text-center font-semibold border-b-2 transition-colors ${
                    activeCategory === 'insurer'
                      ? 'border-[#00387A] text-[#00387A] bg-white'
                      : 'border-transparent text-slate-500 hover:text-slate-800'
                  }`}
                >
                  Insurer / Underwriter
                </button>
                <button
                  type="button"
                  onClick={() => setActiveCategory('mca')}
                  className={`flex-1 py-2 text-center font-semibold border-b-2 transition-colors ${
                    activeCategory === 'mca'
                      ? 'border-[#00387A] text-[#00387A] bg-white'
                      : 'border-transparent text-slate-500 hover:text-slate-800'
                  }`}
                >
                  MCA Surveyors
                </button>
              </div>

              {/* Category Items List */}
              <div className="max-h-60 overflow-y-auto divide-y divide-slate-100 p-1">
                {activeCategory === 'shipping' &&
                  staffData.shipping_lines.map((item, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => handleAddAttendee(item)}
                      className="w-full text-left p-2 hover:bg-blue-50 rounded transition-colors flex items-start justify-between gap-2"
                    >
                      <div>
                        <div className="font-semibold text-slate-900">{item.name}</div>
                        <div className="text-[11px] text-slate-500">{item.designation}</div>
                        <div className="text-[10px] text-blue-700 mt-0.5">{item.representing}</div>
                      </div>
                      <span className="shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded bg-blue-100 text-blue-800">
                        {item.line}
                      </span>
                    </button>
                  ))}

                {activeCategory === 'shipper' &&
                  staffData.shippers.map((item, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => handleAddAttendee(item)}
                      className="w-full text-left p-2 hover:bg-blue-50 rounded transition-colors"
                    >
                      <div className="font-semibold text-slate-900">{item.name}</div>
                      <div className="text-[11px] text-slate-500">{item.designation}</div>
                      <div className="text-[10px] text-emerald-700 mt-0.5">{item.representing}</div>
                    </button>
                  ))}

                {activeCategory === 'insurer' &&
                  staffData.cargo_insurers.map((item, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => handleAddAttendee(item)}
                      className="w-full text-left p-2 hover:bg-blue-50 rounded transition-colors"
                    >
                      <div className="font-semibold text-slate-900">{item.name}</div>
                      <div className="text-[11px] text-slate-500">{item.designation}</div>
                      <div className="text-[10px] text-purple-700 mt-0.5">{item.representing}</div>
                    </button>
                  ))}

                {activeCategory === 'mca' &&
                  staffData.mca_surveyors.map((item, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => handleAddAttendee(item)}
                      className="w-full text-left p-2 hover:bg-blue-50 rounded transition-colors"
                    >
                      <div className="font-semibold text-slate-900">{item.name}</div>
                      <div className="text-[11px] text-slate-500">{item.designation}</div>
                      <div className="text-[10px] text-slate-600 mt-0.5">{item.representing}</div>
                    </button>
                  ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

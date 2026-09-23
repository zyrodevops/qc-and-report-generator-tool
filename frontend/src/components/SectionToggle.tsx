import React from 'react';

/**
 * "In report" tick box.
 *
 * Unticking leaves a section, row or chart out of the preview and the Word/PDF.
 * Nothing is deleted — ticking it again brings it back exactly as it was.
 * A missing flag counts as ticked, so older reports are unaffected.
 */
export const isIncluded = (flag: unknown) => flag !== false;

export const SectionToggle: React.FC<{
  checked: boolean;
  onChange: (next: boolean) => void;
  label?: string;
  title?: string;
  compact?: boolean;
}> = ({ checked, onChange, label = 'In report', title, compact = false }) => (
  <label
    className={`inline-flex items-center gap-1.5 cursor-pointer select-none shrink-0 ${
      compact ? 'text-[11px]' : 'text-xs'
    } ${checked ? 'text-emerald-700' : 'text-gray-400'}`}
    title={title || (checked ? 'Untick to leave this out of the report' : 'Tick to put this back in the report')}
  >
    <input
      type="checkbox"
      checked={checked}
      onChange={(e) => onChange(e.target.checked)}
      className="w-4 h-4 accent-emerald-600 cursor-pointer"
    />
    {label && <span className="font-medium">{label}</span>}
  </label>
);

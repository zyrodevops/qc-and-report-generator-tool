import React from 'react';
import { Check } from 'lucide-react';

/** Keys as the wording library tags its sentences (gc_clause_library.LOSS_WORDS). */
export const LOSS_TYPES: { key: string; label: string }[] = [
  { key: 'wet', label: 'Wet / water' },
  { key: 'breakage', label: 'Breakage / dents' },
  { key: 'shortage', label: 'Shortage / pilferage' },
  { key: 'leakage', label: 'Leakage' },
  { key: 'rust', label: 'Rust' },
  { key: 'contamination', label: 'Contamination' },
  { key: 'accident', label: 'Accident in transit' },
];

interface Props {
  value: string[];
  onChange: (next: string[]) => void;
}

/**
 * What kind of loss this is. The standard wording offered in each section
 * follows it: rainfall records and the salinity test for a wet loss, seal
 * tampering for a shortage. More than one can be picked.
 */
export const LossTypePicker: React.FC<Props> = ({ value, onChange }) => {
  const toggle = (key: string) =>
    onChange(value.includes(key) ? value.filter((k) => k !== key) : [...value, key]);
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5" data-testid="loss-types">
      <div className="text-sm font-bold text-gray-800">Type of loss</div>
      <div className="text-xs text-gray-500 mb-2">
        Pick all that apply. The standard wording in each section follows this.
      </div>
      <div className="flex flex-wrap gap-2">
        {LOSS_TYPES.map((t) => {
          const on = value.includes(t.key);
          return (
            <button
              key={t.key}
              type="button"
              aria-pressed={on}
              onClick={() => toggle(t.key)}
              className={`inline-flex items-center gap-1 text-xs px-3 py-1 rounded-full border ${
                on
                  ? 'border-blue-500 bg-blue-50 text-blue-800 font-semibold'
                  : 'border-gray-300 bg-white text-gray-700 hover:border-blue-400'
              }`}
            >
              {on && <Check size={12} />}
              {t.label}
            </button>
          );
        })}
      </div>
      {value.length === 0 && (
        <div className="text-[11px] text-amber-700 mt-2">
          None picked: only wording that fits any loss is offered.
        </div>
      )}
    </div>
  );
};

export default LossTypePicker;

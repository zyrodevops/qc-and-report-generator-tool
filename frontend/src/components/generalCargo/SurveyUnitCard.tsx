import React, { useMemo, useState } from 'react';
import { ClipboardList, Trash2, ChevronUp, ChevronDown } from 'lucide-react';
import { NarrativeBlock } from '../preview/blocks/NarrativeBlock';
import { AttendanceEditor } from './AttendanceEditor';
import { FindingsEditor } from './FindingsEditor';
import { UnitTablesEditor } from './UnitTablesEditor';
import { ClauseContext } from '../../api/client';
import { surveyUnitValues } from '../../utils/clauseContext';

interface Props {
  block: any;
  heading: string;
  onChange: (b: any) => void;
  onRemove?: () => void;
  onMove?: (dir: -1 | 1) => void;
  containers: string[];
  clauseContext?: ClauseContext;
  /** The containers as the documents give them (weights, tare), when documents were applied. */
  shipmentContainers?: any[];
}

/**
 * One OUR SURVEY paragraph: a visit, or one container's inspection. The
 * client's reports have one per container, or one per survey day.
 */
export const SurveyUnitCard: React.FC<Props> = ({ block, heading, onChange, onRemove, onMove, containers, clauseContext, shipmentContainers }) => {
  const [people, setPeople] = useState((block.attendance || []).length > 0);
  // The wording offered here names this paragraph's date, place, container and
  // who attended, not the first paragraph's.
  const unitContext = useMemo(() => {
    if (!clauseContext) return undefined;
    const values: Record<string, any> = { ...clauseContext.values };
    for (const k of ['survey_date', 'place_of_survey', 'representative']) delete values[k];
    Object.assign(values, surveyUnitValues(block));
    return { ...clauseContext, values };
  }, [clauseContext, block]);
  const listId = `survey-containers-${block.id}`;
  const field = (key: string, label: string, placeholder: string, extra: any = {}) => (
    <label className="text-xs text-gray-600 flex flex-col gap-1">
      {label}
      <input
        value={block[key] || ''}
        placeholder={placeholder}
        aria-label={`${label} (${block.id})`}
        onChange={(e) => onChange({ ...block, [key]: e.target.value })}
        className="px-2 py-1.5 border border-gray-300 rounded text-sm text-gray-800 outline-none focus:ring-1 focus:ring-blue-500"
        {...extra}
      />
    </label>
  );

  return (
    <div className="bg-white rounded-xl shadow-sm border border-blue-100 p-5 space-y-4" data-testid="survey-unit">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 font-bold text-gray-800">
          <ClipboardList className="w-5 h-5 text-blue-600" />
          <span className="text-sm">{heading}</span>
        </div>
        <div className="flex items-center gap-1">
          {onMove && (
            <>
              <button type="button" onClick={() => onMove(-1)} className="p-1 text-gray-400 hover:text-blue-600" aria-label="Move up">
                <ChevronUp className="w-4 h-4" />
              </button>
              <button type="button" onClick={() => onMove(1)} className="p-1 text-gray-400 hover:text-blue-600" aria-label="Move down">
                <ChevronDown className="w-4 h-4" />
              </button>
            </>
          )}
          {onRemove && (
            <button
              type="button"
              onClick={onRemove}
              className="flex items-center gap-1 text-xs text-red-600 border border-red-200 hover:bg-red-50 px-2 py-1 rounded ml-1"
            >
              <Trash2 className="w-3.5 h-3.5" /> Remove
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {field('survey_date', 'Survey date', 'e.g. 22 June 2026')}
        {field('place', 'Place (optional)', 'e.g. the CFS at Nhava Sheva')}
        {field('container', 'Container No. (optional)', 'e.g. TSTU1234565', { list: containers.length ? listId : undefined })}
        {containers.length > 0 && (
          <datalist id={listId}>
            {containers.map((c) => (
              <option key={c} value={c} />
            ))}
          </datalist>
        )}
      </div>
      <div className="flex items-center gap-6 text-xs text-gray-700">
        <label className="inline-flex items-center gap-1.5 cursor-pointer select-none">
          <input type="checkbox" checked={Boolean(block.joint)} onChange={(e) => onChange({ ...block, joint: e.target.checked })} />
          Joint survey (heading reads "OUR JOINT SURVEY")
        </label>
        <label className="inline-flex items-center gap-1.5 cursor-pointer select-none">
          <input type="checkbox" checked={people} onChange={(e) => setPeople(e.target.checked)} />
          People attended this visit
        </label>
      </div>

      {people && (
        <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
          <AttendanceEditor
            rows={block.attendance || []}
            intro={block.attendance_intro ?? 'The following persons attended the survey:'}
            label="Attended this visit (printed after the first paragraph)"
            onChange={(rows, intro) => onChange({ ...block, attendance: rows, attendance_intro: intro })}
          />
        </div>
      )}

      <NarrativeBlock
        block={block}
        heading="What was found"
        clauseSection="survey_findings"
        onChange={onChange}
        editable
        clauseContext={unitContext}
      />

      <FindingsEditor block={block} onChange={onChange} clauseContext={unitContext} />
      <UnitTablesEditor
        block={block}
        onChange={onChange}
        fromDocuments={(shipmentContainers || []).find((c: any) => c.container === String(block.container || '').replace(/\s/g, '').toUpperCase())}
      />
    </div>
  );
};

export default SurveyUnitCard;

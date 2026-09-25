import React from 'react';
import { getRecorderChartUrl } from '../../../api/client';

/** Same columns the Word / PDF output prints. */
const COLUMNS = ['Recorder', 'Container', 'Start', 'Stop', 'Trip length', 'Highest', 'Lowest', 'Average', 'MKT'];

const when = (iso?: string, raw?: string) => {
  if (iso) {
    const d = new Date(iso);
    if (!Number.isNaN(d.getTime())) {
      const mon = d.toLocaleString('en-GB', { month: 'short' });
      const hh = String(d.getHours()).padStart(2, '0');
      const mm = String(d.getMinutes()).padStart(2, '0');
      return `${d.getDate()} ${mon} ${d.getFullYear()} ${hh}:${mm}`;
    }
  }
  return raw || '';
};
const deg = (v: any) => (v === undefined || v === null || v === '' ? '' : `${v} °C`);

export interface RecordersBlockProps {
  block: any;
  reportId?: string;
  /** Form editor: the section and graph ticks can be changed. */
  onChange?: (updatedBlock: any) => void;
}

/**
 * Temperature recorders: the devices' own printed summary, and a graph of
 * each recorder's readings. The graphs can be left out of the report.
 */
export const RecordersBlock: React.FC<RecordersBlockProps> = ({ block, reportId, onChange }) => {
  const recs: any[] = (block?.recorders || []).filter((r: any) => r.included !== false);
  if (!recs.length) return null;
  const showChart = block?.show_chart !== false;
  const offsets = Array.from(new Set(recs.map((r) => r.utc_offset).filter(Boolean)));

  return (
    <div className="recorders-block my-2">
      <h2 className="text-[12px] font-bold text-[#00387A] uppercase tracking-wider border-b border-slate-300 pb-1 mb-2">
        {block.title || 'TEMPERATURE RECORDER SUMMARY'}
      </h2>
      <div className="overflow-x-auto">
        <table className="w-full text-[10px] border border-slate-300">
          <thead className="bg-slate-100">
            <tr>
              {COLUMNS.map((c) => (
                <th key={c} className="border border-slate-300 px-1.5 py-1 text-left font-semibold">{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {recs.map((r, i) => (
              <tr key={r.asset_id || i}>
                {[r.device_id, r.container, when(r.start_iso, r.start), when(r.stop_iso, r.stop), r.trip_length,
                  deg(r.highest_c), deg(r.lowest_c), deg(r.average_c), deg(r.mkt_c)].map((v, j) => (
                  <td key={j} className="border border-slate-300 px-1.5 py-1 font-mono whitespace-nowrap">{v ?? ''}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[9px] text-slate-500 mt-1">
        Times as recorded by the devices{offsets.length === 1 ? ` (UTC ${offsets[0]})` : ''}.
      </p>

      {onChange && (
        <label className="inline-flex items-center gap-1.5 text-xs text-slate-700 mt-2 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={showChart}
            onChange={(e) => onChange({ ...block, show_chart: e.target.checked })}
          />
          Include the temperature graph{recs.length > 1 ? 's' : ''} in the report
        </label>
      )}

      {showChart && reportId && (
        <div className="space-y-2 mt-2">
          {recs.map((r, i) =>
            r.asset_id ? (
              <img
                key={r.asset_id || i}
                src={getRecorderChartUrl(reportId, r.asset_id)}
                alt={`Temperature graph, recorder ${r.device_id || ''}`}
                className="w-full border border-slate-200 rounded"
              />
            ) : null,
          )}
        </div>
      )}
    </div>
  );
};

import React from 'react';
import { getRecorderChartUrl } from '../../../api/client';

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

const verticalSummaryRows = (r: any): [string, string][] => {
  const rows: [string, string][] = [];
  if (r.start_delay) rows.push(['Start Delay', String(r.start_delay)]);
  if (r.interval) rows.push(['Log Interval', String(r.interval)]);
  const startStr = when(r.start_iso, r.start);
  if (startStr) rows.push(['First Point', startStr]);
  const stopStr = when(r.stop_iso, r.stop);
  if (stopStr) rows.push(['Stop Time', stopStr]);
  if (r.data_points) rows.push(['No. of Points', String(r.data_points)]);
  if (r.trip_length) rows.push(['Trip Length', String(r.trip_length)]);

  if (r.highest_c !== undefined && r.highest_c !== null && r.highest_c !== '') {
    let hStr = deg(r.highest_c);
    if (r.highest_c_time) hStr += ` @${r.highest_c_time}`;
    rows.push(['High Extreme', hStr]);
  }

  if (r.lowest_c !== undefined && r.lowest_c !== null && r.lowest_c !== '') {
    let lStr = deg(r.lowest_c);
    if (r.lowest_c_time) lStr += ` @${r.lowest_c_time}`;
    rows.push(['Low Extreme', lStr]);
  }

  if (r.average_c !== undefined && r.average_c !== null && r.average_c !== '') {
    rows.push(['Average', deg(r.average_c)]);
  }

  if (r.mkt_c !== undefined && r.mkt_c !== null && r.mkt_c !== '') {
    rows.push(['MKT', deg(r.mkt_c)]);
  }

  if (r.alarm_status) rows.push(['Alarm Status', String(r.alarm_status)]);
  return rows;
};

const recorderTableHeader = (r: any, idx: number) => {
  const dev = String(r.device_id || '—').trim();
  const cont = r.container ? ` # ${r.container}` : '';
  const annexureLetter = String.fromCharCode(65 + idx);
  return `Recorder Trip Sr. No. ${dev}${cont} (Copy of the temperature recording (PDF File) is attached as Annexure ${annexureLetter})`;
};

export interface RecordersBlockProps {
  block: any;
  reportId?: string;
  /** Form editor: the section and graph ticks can be changed. */
  onChange?: (updatedBlock: any) => void;
  hideTitle?: boolean;
  isFormEditor?: boolean;
}

/**
 * Temperature recorders: the devices' own printed summary as authentic vertical
 * 2-column tables, paired container-by-container with its readings graph.
 */
export const RecordersBlock: React.FC<RecordersBlockProps> = ({
  block,
  reportId,
  onChange,
  hideTitle,
  isFormEditor = false,
}) => {
  const recs: any[] = (block?.recorders || []).filter((r: any) => r.included !== false);
  if (!recs.length) return null;
  const showChart = block?.show_chart !== false;
  const offsets = Array.from(new Set(recs.map((r) => r.utc_offset).filter(Boolean)));

  return (
    <div className="recorders-block my-2">
      {!hideTitle && block.title && (
        <h2 className="text-[12px] font-bold text-[#00387A] uppercase tracking-wider border-b border-slate-300 pb-1 mb-2">
          {block.title}
        </h2>
      )}

      {isFormEditor && onChange && (
        <div className="mb-3">
          <label className="inline-flex items-center gap-1.5 text-xs text-slate-700 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={showChart}
              onChange={(e) => onChange({ ...block, show_chart: e.target.checked })}
            />
            Include temperature graph{recs.length > 1 ? 's' : ''} paired with container summary in the report
          </label>
        </div>
      )}

      <div className="space-y-4">
        {recs.map((r, i) => {
          const vRows = verticalSummaryRows(r);
          return (
            <div key={r.asset_id || i} className="border border-slate-300 rounded overflow-hidden">
              <div className="bg-slate-100 px-3 py-1.5 font-bold text-[11px] text-[#00387A] border-b border-slate-300">
                {recorderTableHeader(r, i)}
              </div>
              <table className="w-full text-xs">
                <tbody>
                  {vRows.map(([param, val], j) => (
                    <tr key={j} className={j % 2 === 0 ? 'bg-white' : 'bg-slate-50/60'}>
                      <td className="w-2/5 px-3 py-1 font-semibold text-slate-700 text-[11px] border-r border-slate-200 border-b border-slate-100">
                        {param}
                      </td>
                      <td className="w-3/5 px-3 py-1 text-slate-900 font-mono text-[11px] border-b border-slate-100">
                        {val}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {showChart && reportId && r.asset_id && (
                <div className="p-3 bg-slate-50/50 border-t border-slate-200 flex flex-col items-center">
                  <div className="w-full flex justify-center">
                    <img
                      src={getRecorderChartUrl(reportId, r.asset_id)}
                      alt={`Temperature graph, recorder ${r.device_id || ''}`}
                      className="w-full h-auto object-contain border border-slate-300 rounded bg-white shadow-xs"
                      style={{ maxWidth: '16cm' }}
                    />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <p className="text-[9px] text-slate-500 mt-2">
        Times as recorded by the devices{offsets.length === 1 ? ` (UTC ${offsets[0]})` : ''}.
      </p>
    </div>
  );
};


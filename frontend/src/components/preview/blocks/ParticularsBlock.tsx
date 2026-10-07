import React from 'react';
import { normalizeVoyageAsync } from '../../../utils/portNormalizer';
import { useHouseStyle } from '../../../utils/houseStyle';

const BOLD_LINE = /^\s*(?:Total\b|Net Weight\b|Gross Weight\b)/i;

/** The value as the Word file prints it: a party's name (first line) and total / weight lines bold. */
const CoverValue: React.FC<{ label: string; value: string }> = ({ label, value }) => {
  const lines = value.split('\n');
  const party = /^(shipper|consignees?)$/i.test(label.trim().replace(/:$/, '')) && lines.length > 1;
  return (
    <>
      {lines.map((l, i) => (
        <div key={i} style={{ fontWeight: (party && i === 0) || BOLD_LINE.test(l) ? 700 : 400, textAlign: /packing/i.test(label) ? 'justify' : 'left' }}>
          {l || '\u00a0'}
        </div>
      ))}
    </>
  );
};

/** Survey report preview: the value shows as printed; a click opens a box to edit (line breaks kept). */
const CoverCell: React.FC<{ label: string; value: string; onChange?: (v: string) => void }> = ({ label, value, onChange }) => {
  const [editing, setEditing] = React.useState(false);
  if (editing && onChange) {
    return (
      <textarea
        autoFocus
        value={value}
        rows={Math.max(1, value.split('\n').length)}
        onChange={(e) => onChange(e.target.value)}
        onBlur={async (e) => {
          setEditing(false);
          if (/voyage/i.test(label)) {
            const normalized = await normalizeVoyageAsync(e.target.value);
            if (normalized && normalized !== e.target.value) onChange(normalized);
          }
        }}
        className="mca-textarea w-full bg-white outline-none ring-1 ring-blue-500 resize-y"
        style={{ textAlign: 'left' }}
      />
    );
  }
  return (
    <div className={onChange ? 'cursor-text hover:bg-blue-50/40' : ''} onClick={() => onChange && setEditing(true)} title={onChange ? 'Click to edit' : undefined}>
      <CoverValue label={label} value={value} />
    </div>
  );
};

export interface ParticularsBlockProps {
  block: any;
  transport?: any;
  carriageUnits?: any[];
  weights?: any;
  onChange?: (updatedBlock: any) => void;
  editable?: boolean;
  /** Survey report preview: only rows [from, to) — the table continues on the next page. */
  rowRange?: [number, number];
}

export const ParticularsBlock: React.FC<ParticularsBlockProps> = ({
  block,
  onChange,
  editable = true,
  rowRange,
}) => {
  const rows: any[] = block?.rows || [];
  const house = useHouseStyle();
  if (rows.length === 0) return null;

  const sectionTitle = block.section === '' ? '' : block.section || '';

  const handleValueChange = (rIdx: number, newVal: string) => {
    if (!onChange) return;
    const newRows = [...rows];
    if (Array.isArray(newRows[rIdx]?.value)) {
      newRows[rIdx] = { ...newRows[rIdx], value: [newVal] };
    } else {
      newRows[rIdx] = { ...newRows[rIdx], value: newVal };
    }
    onChange({ ...block, rows: newRows });
  };

  const handleConsignmentCellChange = (rIdx: number, itemIdx: number, key: string, newVal: string) => {
    if (!onChange) return;
    const newRows = [...rows];
    const targetRow = { ...newRows[rIdx] };
    const items = [...(targetRow.rows || targetRow.items || [])];
    items[itemIdx] = { ...items[itemIdx], [key]: newVal };
    targetRow.rows = items;
    newRows[rIdx] = targetRow;
    onChange({ ...block, rows: newRows });
  };

  const handleFooterChange = (rIdx: number, newFooter: string) => {
    if (!onChange) return;
    const newRows = [...rows];
    newRows[rIdx] = { ...newRows[rIdx], footer: newFooter, value: [newFooter] };
    onChange({ ...block, rows: newRows });
  };

  return (
    <div
      className={house ? "particulars-block" : "particulars-block my-2"}
      // Survey reports: a blank line after the table (as in Word), none between its continued rows.
      style={house && (!rowRange || rowRange[1] >= rows.length) ? { marginBottom: "12.65pt" } : undefined}
    >
      {sectionTitle && (
        <h2 className="text-[12px] font-bold text-[#00387A] uppercase tracking-wider border-b border-slate-300 pb-1 mb-2">
          {sectionTitle}
        </h2>
      )}
      <table className={`w-full border-collapse border border-slate-400 text-xs ${house ? 'mca-particulars' : ''}`}>
        <tbody>
          {rows.map((row, idx) => {
            if (rowRange && (idx < rowRange[0] || idx >= rowRange[1])) return null;
            const label = row.label || '';
            const isTable =
              row.type === 'table' ||
              Boolean(row.headers) ||
              (label.toLowerCase().includes('consignment') && (Boolean(row.rows) || Boolean(row.items)));

            if (isTable) {
              const headers = row.headers || ['Commodity / Variety', 'Count / Size', 'Total Boxes'];
              const subItems: any[] = row.rows || row.items || [];
              const footer = row.footer || '';

              return (
                <tr key={idx} className="border-b border-slate-400">
                  <td className="w-[28%] bg-slate-50 font-semibold text-slate-800 px-3 py-1.5 border-r border-slate-400 align-top">
                    {label}
                  </td>
                  <td className="w-[4%] text-center text-slate-700 px-1 py-1.5 border-r border-slate-400 align-top font-bold">
                    :
                  </td>
                  <td className="w-[68%] text-slate-900 p-0 font-sans align-top">
                    <table className="w-full border-collapse text-xs">
                      <thead>
                        <tr className="bg-slate-100 font-bold border-b border-slate-400">
                          <th className="border-r border-slate-400 px-2 py-1 text-left font-semibold">{headers[0]}</th>
                          <th className="border-r border-slate-400 px-2 py-1 text-center font-semibold">{headers[1]}</th>
                          <th className="px-2 py-1 text-right font-semibold">{headers[2]}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {subItems.map((item: any, sIdx: number) => {
                          const col1 = item.col1 ?? item.variety ?? item.description ?? '';
                          const col2 = item.col2 ?? item.count ?? item.size ?? item.count_size ?? '';
                          const col3 = item.col3 ?? item.boxes ?? item.cartons ?? item.total_boxes ?? '';

                          return (
                            <tr key={sIdx} className="border-b border-slate-300">
                              <td className="border-r border-slate-400 px-2 py-1">
                                {editable && onChange ? (
                                  <input
                                    type="text"
                                    value={col1}
                                    onChange={(e) => handleConsignmentCellChange(idx, sIdx, 'col1', e.target.value)}
                                    className="w-full bg-transparent border-none outline-none focus:bg-white focus:ring-1 focus:ring-blue-500"
                                  />
                                ) : (
                                  col1
                                )}
                              </td>
                              <td className="border-r border-slate-400 px-2 py-1 text-center">
                                {editable && onChange ? (
                                  <input
                                    type="text"
                                    value={col2}
                                    onChange={(e) => handleConsignmentCellChange(idx, sIdx, 'col2', e.target.value)}
                                    className="w-full bg-transparent border-none outline-none text-center focus:bg-white focus:ring-1 focus:ring-blue-500"
                                  />
                                ) : (
                                  col2
                                )}
                              </td>
                              <td className="px-2 py-1 text-right">
                                {editable && onChange ? (
                                  <input
                                    type="text"
                                    value={col3}
                                    onChange={(e) => handleConsignmentCellChange(idx, sIdx, 'col3', e.target.value)}
                                    className="w-full bg-transparent border-none outline-none text-right focus:bg-white focus:ring-1 focus:ring-blue-500"
                                  />
                                ) : (
                                  col3
                                )}
                              </td>
                            </tr>
                          );
                        })}
                        {footer && (
                          <tr className="bg-slate-50 font-semibold border-t border-slate-400">
                            <td colSpan={3} className="px-2 py-1">
                              {editable && onChange ? (
                                <input
                                  type="text"
                                  value={footer}
                                  onChange={(e) => handleFooterChange(idx, e.target.value)}
                                  className="w-full bg-transparent border-none outline-none font-semibold focus:bg-white focus:ring-1 focus:ring-blue-500"
                                />
                              ) : (
                                footer
                              )}
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </td>
                </tr>
              );
            }

            const rawVal = row.value;
            let valStr = '';

            if (Array.isArray(rawVal)) {
              const parts: string[] = [];
              rawVal.forEach((item) => {
                if (item && typeof item === 'object' && 'amount' in item) {
                  const curr = item.currency || '';
                  parts.push(`${curr} ${item.amount}`.trim());
                } else if (Array.isArray(item)) {
                  parts.push(item.join(', '));
                } else if (item !== undefined && item !== null) {
                  parts.push(String(item));
                }
              });
              valStr = parts.join(', ');
            } else if (rawVal !== undefined && rawVal !== null) {
              valStr = String(rawVal);
            }

            if (row.note && !editable) {
              valStr += ` (${row.note})`;
            }

            return (
              <tr key={idx} className="border-b border-slate-400">
                <td className="w-[28%] bg-slate-50 font-semibold text-slate-800 px-3 py-1.5 border-r border-slate-400 align-top">
                  {label}
                </td>
                <td className="w-[4%] text-center text-slate-700 px-1 py-1.5 border-r border-slate-400 align-top font-bold">
                  :
                </td>
                <td className="w-[68%] text-slate-900 p-0 font-sans align-top">
                  {house ? (
                    <CoverCell label={label} value={valStr} onChange={editable && onChange ? (v) => handleValueChange(idx, v) : undefined} />
                  ) : editable && onChange ? (
                    label.toLowerCase().includes('packing') ? (
                      <textarea
                        value={valStr}
                        rows={3}
                        onChange={(e) => handleValueChange(idx, e.target.value)}
                        className="w-full bg-transparent px-3 py-1.5 border-none outline-none hover:bg-blue-50/40 focus:bg-white focus:ring-1 focus:ring-blue-500 text-xs text-slate-900 font-sans transition-colors resize-y"
                      />
                    ) : (
                      <input
                        type="text"
                        value={valStr}
                        onChange={(e) => handleValueChange(idx, e.target.value)}
                        onBlur={async (e) => {
                          if (/voyage/i.test(label)) {
                            const val = e.target.value;
                            const normalized = await normalizeVoyageAsync(val);
                            if (normalized && normalized !== val) {
                              handleValueChange(idx, normalized);
                            }
                          }
                        }}
                        className="w-full h-full bg-transparent px-3 py-1.5 border-none outline-none hover:bg-blue-50/40 focus:bg-white focus:ring-1 focus:ring-blue-500 text-xs text-slate-900 font-sans transition-colors cursor-text"
                      />
                    )
                  ) : (
                    <div className="px-3 py-1.5 whitespace-pre-wrap">{valStr}</div>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

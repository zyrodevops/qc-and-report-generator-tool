import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  Check,
  CloudUpload,
  Info,
  Loader2,
  Minus,
  Plus,
  ScanLine,
  Trash2,
  Upload,
  X,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';
import {
  applyTallyGrid,
  fetchTallyCapabilities,
  uploadTallySheet,
  uploadTallySpreadsheet,
  TallyCapabilities,
  TallyCategory,
  TallyExtraction,
  TallyRow,
} from '../../api/client';
import { columnTitle } from '../../utils/labels';

/**
 * Verification Workbench.
 *
 * The sheet photograph on the left, the grid on the right, and the surveyor
 * moving between them. Focusing a cell zooms the photo to the handwriting that
 * cell came from, so checking a number means glancing left rather than hunting
 * across a page.
 *
 * The row check compares what is in the cells against the total the surveyor
 * wrote at the end of the row. Those are two independent numbers, so when they
 * disagree something really is wrong. A row with no written total is marked as
 * unchecked rather than passed — it has not been verified, and showing a green
 * tick for it would be worse than showing nothing.
 */

interface Props {
  reportId: string;
  isOpen: boolean;
  onClose: () => void;
  /** Gets the server's new state and version, so the page's next save does not conflict. */
  onSuccess: (updatedBlockState: any, version: number) => void;
  blockId?: string;
  commodity?: string;
  /** 'spreadsheet' when opened from Import CSV / Excel. */
  sourceHint?: 'any' | 'spreadsheet';
  /** The figures already saved in the report, so they can be reopened and corrected. */
  existing?: { categories: TallyCategory[]; rows: any[]; unit?: string };
}

/**
 * A row as it exists while being checked. Unlike the stored shape, a cell may
 * be null: that is an unread cell the surveyor still has to fill, and it has to
 * stay distinguishable from a genuine zero right up until he types something.
 */
type RowState = Omit<TallyRow, 'values'> & {
  values: Record<string, number | null>;
  /** Kept when saved rows are reopened, so each stays with its container. */
  container?: string;
};

interface FocusedCell {
  rowIdx: number;
  catKey: string;
}

/**
 * A figure from the server as a number. Weights arrive as text ("0.820") so
 * they keep their three places over the wire; left as text they were skipped
 * by every sum here, and each grapes row read as 0.000.
 */
const asNum = (v: any): number | null => {
  if (v === null || v === undefined || String(v).trim() === '') return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
};

const toRowState = (r: TallyRow): RowState => ({
  ...r,
  values: Object.fromEntries(Object.entries(r.values || {}).map(([k, v]) => [k, asNum(v)])),
  stated_total: asNum(r.stated_total),
});

const MIN_ZOOM = 1;
const MAX_ZOOM = 6;

export const VerificationWorkbench: React.FC<Props> = ({
  reportId,
  isOpen,
  onClose,
  onSuccess,
  blockId,
  commodity,
  sourceHint = 'any',
  existing,
}) => {
  const [caps, setCaps] = useState<TallyCapabilities | null>(null);
  const [extraction, setExtraction] = useState<TallyExtraction | null>(null);
  const [rows, setRows] = useState<RowState[]>([]);
  const [categories, setCategories] = useState<TallyCategory[]>([]);
  const [headers, setHeaders] = useState<Record<string, any>>({});

  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [focused, setFocused] = useState<FocusedCell | null>(null);
  const [zoom, setZoom] = useState(1);
  const [addingColumn, setAddingColumn] = useState(false);
  const [newColumn, setNewColumn] = useState('');
  const [showHeader, setShowHeader] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);
  // Kept so a spreadsheet can be re-read when the surveyor maps a column.
  const lastFile = useRef<File | null>(null);

  // ---------------------------------------------------------------- capabilities
  useEffect(() => {
    if (!isOpen) return;
    let cancelled = false;
    fetchTallyCapabilities(reportId, commodity)
      .then((c) => {
        if (cancelled) return;
        setCaps(c);
        setCategories(c.categories);
      })
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [isOpen, reportId, commodity]);

  // Reset when the dialog closes so the next sheet starts clean.
  useEffect(() => {
    if (isOpen) return;
    setExtraction(null);
    setRows([]);
    setHeaders({});
    setFocused(null);
    setError(null);
  }, [isOpen]);

  // --------------------------------------------------------------------- upload
  const handleFile = useCallback(
    async (file: File) => {
      setLoading(true);
      setError(null);
      setFocused(null);
      lastFile.current = file;
      try {
        const isSheet = /\.(csv|xlsx|xlsm|xls)$/i.test(file.name);
        const result = isSheet
          ? await uploadTallySpreadsheet(reportId, file, { commodity })
          : await uploadTallySheet(reportId, file, { commodity });
        setExtraction(result);
        setCategories(result.table.categories);
        setHeaders(result.headers || {});
        setRows(result.table.rows.map(toRowState));
      } catch (e: any) {
        setError(e.message || 'Could not read that file.');
      } finally {
        setLoading(false);
      }
    },
    [reportId, commodity],
  );

  // ------------------------------------------------------------------ live check
  // Grapes, blueberries and cherries are weighed, not counted: 0.820 kg a box.
  const unit = extraction?.table.unit || caps?.unit || 'pcs';
  const isKg = unit.toLowerCase() === 'kg';
  // Weights are added in whole grams. In plain JS 0.82 + 0.52 + 0.12 is
  // 1.4599999999999997, which would mark a correct row as not tying out.
  const scale = isKg ? 1000 : 1;
  const toUnits = (v: number) => Math.round(v * scale);
  const fmt = (v: number | null | undefined) =>
    v === null || v === undefined ? '' : isKg ? v.toFixed(3) : String(v);

  /**
   * Columns that hold a figure in at least one row. A fruit's list has columns
   * a given sheet never uses — the grapes sheet has no Decay or Blackish — and
   * those cells are empty because the column is not on the sheet, not because
   * the reader failed. Counting them made every row "could not be read". When
   * nothing has been entered anywhere, every column counts, so a fresh grid
   * still shows what is left to fill.
   */
  const activeKeys = useMemo(() => {
    const used = new Set(
      categories
        .filter((c) => rows.some((r) => typeof r.values[c.key] === 'number'))
        .map((c) => c.key),
    );
    return used.size ? used : new Set(categories.map((c) => c.key));
  }, [rows, categories]);

  /**
   * Recomputed on every keystroke. Deliberately the same arithmetic the server
   * redoes on save, so what the surveyor signs off is what gets stored.
   */
  const checks = useMemo(
    () =>
      rows.map((row) => {
        const units = categories.reduce((sum, cat) => {
          const v = row.values[cat.key];
          return sum + (typeof v === 'number' && !Number.isNaN(v) ? toUnits(v) : 0);
        }, 0);
        const computed = units / scale;
        const hasBlank = categories.some(
          (c) =>
            activeKeys.has(c.key) &&
            (row.values[c.key] === null || row.values[c.key] === undefined),
        );
        if (row.stated_total === null || row.stated_total === undefined) {
          return { computed, status: 'UNCHECKED' as const, delta: null, hasBlank };
        }
        const deltaUnits = units - toUnits(row.stated_total);
        return {
          computed,
          status: deltaUnits === 0 ? ('OK' as const) : ('MISMATCH' as const),
          delta: deltaUnits / scale,
          hasBlank,
        };
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [rows, categories, scale, activeKeys],
  );

  const mismatchCount = checks.filter((c) => c.status === 'MISMATCH').length;
  const blankCount = checks.filter((c) => c.hasBlank).length;
  const uncheckedCount = checks.filter((c) => c.status === 'UNCHECKED').length;

  const columnTotals = useMemo(() => {
    const totals: Record<string, number> = {};
    categories.forEach((cat) => {
      const units = rows.reduce((sum, r) => {
        const v = r.values[cat.key];
        return sum + (typeof v === 'number' && !Number.isNaN(v) ? toUnits(v) : 0);
      }, 0);
      totals[cat.key] = units / scale;
    });
    return totals;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows, categories, scale]);

  const grandTotal = checks.reduce((s, c) => s + toUnits(c.computed), 0) / scale;
  const rawSheetTotals = extraction?.table.sheet_totals;
  const sheetTotals = rawSheetTotals
    ? {
        values: Object.fromEntries(
          Object.entries(rawSheetTotals.values || {}).map(([k, v]) => [k, asNum(v)]),
        ),
        stated_total: asNum(rawSheetTotals.stated_total),
      }
    : null;

  // ------------------------------------------------------------------- mutations
  /**
   * What a typed cell holds. A weight keeps up to three places (0.820); a count
   * has to be whole, and "2.5" in a count box is left empty for the surveyor
   * rather than cut down to 2.
   */
  const parseFigure = (raw: string): number | null => {
    const text = raw.trim().replace(',', '.');
    if (text === '') return null;
    const n = Number(text);
    if (!Number.isFinite(n) || n < 0) return null;
    if (isKg) return Math.round(n * 1000) / 1000;
    return Number.isInteger(n) ? n : null;
  };

  const setCell = (rowIdx: number, catKey: string, raw: string) => {
    setRows((prev) => {
      const next = [...prev];
      next[rowIdx] = {
        ...next[rowIdx],
        values: { ...next[rowIdx].values, [catKey]: parseFigure(raw) },
      };
      return next;
    });
  };

  const setStatedTotal = (rowIdx: number, raw: string) => {
    setRows((prev) => {
      const next = [...prev];
      next[rowIdx] = { ...next[rowIdx], stated_total: parseFigure(raw) };
      return next;
    });
  };

  const setGroup = (rowIdx: number, val: string) => {
    setRows((prev) => {
      const next = [...prev];
      next[rowIdx] = { ...next[rowIdx], group: val };
      return next;
    });
  };

  const addRow = () => {
    const values: Record<string, number | null> = {};
    categories.forEach((c) => (values[c.key] = null));
    setRows((prev) => [
      ...prev,
      { group: '', boxes_opened: 1, values, stated_total: null, provenance: 'manual' },
    ]);
  };

  const deleteRow = (idx: number) => {
    setRows((prev) => prev.filter((_, i) => i !== idx));
    setFocused(null);
  };

  /**
   * Add a defect column the sheet has and this fruit's list does not.
   *
   * The columns come from the client's own finished reports, but a surveyor can
   * grade against anything he finds in the carton, and a sheet with a column
   * nobody has used before is a normal event rather than a mistake. Without
   * this he would have to leave those counts out, or push them into a column
   * where they do not belong.
   *
   * Cells start empty, not at zero, so the new column does not silently claim
   * every existing row had none of it.
   */
  const addColumn = (rawLabel: string) => {
    const label = rawLabel.trim();
    if (!label) return;

    const key = label.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
    if (!key || categories.some((c) => c.key === key)) {
      setError(`There is already a column called "${label}".`);
      return;
    }

    setCategories((prev) => [...prev, { key, label, role: 'extra' }]);
    setRows((prev) => prev.map((r) => ({ ...r, values: { ...r.values, [key]: null } })));
    setNewColumn('');
    setAddingColumn(false);
    setError(null);
  };

  /**
   * Map a spreadsheet column the automatic matching could not place.
   *
   * Re-reads the file with the surveyor's decision rather than patching the
   * grid in the browser, so the row totals and their checks are recomputed by
   * the same code that produced them in the first place. 'DROP' excludes the
   * column; anything else assigns it.
   */
  const remapSpreadsheetColumn = async (header: string, key: string) => {
    const file = lastFile.current;
    if (!file) return;

    setLoading(true);
    setError(null);
    try {
      const existing = extraction?.spreadsheet?.column_map ?? {};
      const result = await uploadTallySpreadsheet(reportId, file, {
        commodity,
        columnMap: { ...existing, [header]: key },
      });
      setExtraction(result);
      setCategories(result.table.categories);
      setRows(result.table.rows.map(toRowState));
    } catch (e: any) {
      setError(e.message || 'Could not re-read the spreadsheet.');
    } finally {
      setLoading(false);
    }
  };

  /**
   * Remove any column — added here or from the fruit's own list.
   *
   * Removing a column deletes its figures, so if any row has one the surveyor
   * is asked first and told how many. An empty column goes straight away.
   */
  const removeColumn = (key: string) => {
    const cat = categories.find((c) => c.key === key);
    const filled = rows.filter((r) => {
      const v = r.values[key];
      return v !== null && v !== undefined;
    }).length;
    if (
      filled > 0 &&
      !window.confirm(
        `Remove the "${columnTitle(cat?.label || key)}" column?\n\n` +
          `${filled} row${filled > 1 ? 's have' : ' has'} a figure in it. ` +
          `Those figures will be deleted.`,
      )
    ) {
      return;
    }
    setCategories((prev) => prev.filter((c) => c.key !== key));
    setRows((prev) =>
      prev.map((r) => {
        const { [key]: _dropped, ...rest } = r.values;
        return { ...r, values: rest };
      }),
    );
    setFocused(null);
  };

  /**
   * Open the grid without a new file: either blank, or with the figures already
   * saved in the report so a surveyor who comes back later can correct them and
   * save again. Saving goes through the same row checks as a fresh sheet.
   */
  const startManual = (seed?: { categories: TallyCategory[]; rows: any[]; unit?: string }) => {
    const cats = seed?.categories?.length ? seed.categories : caps?.categories || [];
    const toNum = (v: any): number | null => {
      if (v === null || v === undefined || String(v).trim() === '') return null;
      const n = Number(v);
      return Number.isFinite(n) ? n : null;
    };
    const seededRows: RowState[] = seed?.rows?.length
      ? seed.rows.map((r: any) => {
          const values: Record<string, number | null> = {};
          cats.forEach((c) => (values[c.key] = toNum(r.values?.[c.key])));
          return {
            group: r.group || '',
            boxes_opened: r.boxes_opened ?? 1,
            values,
            stated_total: toNum(r.stated_total),
            provenance: r.provenance || 'manual',
            ...(r.container ? { container: String(r.container) } : {}),
          };
        })
      : [
          {
            group: '',
            boxes_opened: 1,
            values: Object.fromEntries(cats.map((c) => [c.key, null])),
            stated_total: null,
            provenance: 'manual',
          },
        ];
    setCategories(cats);
    setRows(seededRows);
    setExtraction({
      extraction_status: 'NO_GRID',
      engines_available: caps?.ocr_engines || [],
      ocr_engine: null,
      quality: { score: 0, is_acceptable: true, warnings: [] },
      headers: {},
      table: {
        commodity: caps?.commodity ?? null,
        unit: seed?.unit || caps?.unit || 'pcs',
        grouping_label: 'Count / Size',
        categories: cats,
        rows: [],
        column_totals: {},
      },
      image: { preview: '', width: 0, height: 0 },
      filename: 'Typed by hand',
    });
  };

  // ---------------------------------------------------------------------- apply
  const handleApply = async () => {
    setApplying(true);
    setError(null);
    try {
      const result = await applyTallyGrid(reportId, {
        headers,
        table: {
          categories,
          unit: extraction?.table.unit || caps?.unit || 'pcs',
          rows: rows.map((r) => ({
            group: r.group,
            boxes_opened: r.boxes_opened ?? 1,
            values: Object.fromEntries(
              categories
                .map((c) => [c.key, r.values[c.key]])
                .filter(([, v]) => typeof v === 'number'),
            ),
            stated_total: r.stated_total,
            ...(r.container ? { container: r.container } : {}),
          })),
        },
        block_id: blockId,
      });
      onSuccess(result.block_state, result.version);
      onClose();
    } catch (e: any) {
      setError(e.message || 'Could not save the tally.');
    } finally {
      setApplying(false);
    }
  };

  if (!isOpen) return null;

  const focusedDetail =
    focused && rows[focused.rowIdx]?.cell_details?.[focused.catKey];
  const focusedBox = focusedDetail?.bbox_norm;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/70 backdrop-blur-sm p-3">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-[1500px] h-[94vh] flex flex-col overflow-hidden">
        {/* ------------------------------------------------------------ header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-blue-50 text-blue-600">
              <ScanLine className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-gray-900">Tally Verification Workbench</h2>
              <p className="text-xs text-gray-500">
                Check each figure against the sheet before it goes into the report
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-700 rounded-lg hover:bg-gray-200 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="mx-5 mt-3 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2.5 text-red-800 text-sm">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* ------------------------------------------------------------- body */}
        {!extraction ? (
          <UploadPane
            caps={caps}
            loading={loading}
            fileInputRef={fileInputRef}
            onFile={handleFile}
            onStartBlank={() => startManual()}
            sourceHint={sourceHint}
            existingCount={existing?.rows?.length || 0}
            onEditExisting={() => startManual(existing)}
          />
        ) : (
          <div className="flex-1 grid grid-cols-12 gap-0 overflow-hidden">
            {/* ------------------------------------------------ left: the sheet */}
            <div className="col-span-4 border-r border-gray-200 bg-slate-100 flex flex-col">
              <div className="px-3 py-2 border-b border-gray-200 bg-white flex items-center justify-between">
                <span className="text-xs font-medium text-gray-600 truncate max-w-[150px]">
                  {extraction.filename}
                </span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setZoom((z) => Math.max(MIN_ZOOM, z - 0.5))}
                    className="p-1.5 text-gray-500 hover:bg-gray-100 rounded"
                    title="Zoom out"
                  >
                    <ZoomOut className="w-3.5 h-3.5" />
                  </button>
                  <span className="text-[11px] font-mono text-gray-500 w-8 text-center">
                    {zoom.toFixed(1)}x
                  </span>
                  <button
                    onClick={() => setZoom((z) => Math.min(MAX_ZOOM, z + 0.5))}
                    className="p-1.5 text-gray-500 hover:bg-gray-100 rounded"
                    title="Zoom in"
                  >
                    <ZoomIn className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="ml-1 text-xs text-blue-600 hover:text-blue-800 font-medium px-2"
                  >
                    Change
                  </button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*,.csv,.xlsx,.xlsm,.xls"
                    className="hidden"
                    onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
                  />
                </div>
              </div>

              <SheetPane
                src={extraction.image.preview}
                box={focusedBox}
                zoom={zoom}
                hasFocus={Boolean(focused)}
              />

              {/* The crop the focused number was read from */}
              <CellInspector
                detail={focusedDetail}
                label={categories.find((c) => c.key === focused?.catKey)?.label}
                rowLabel={focused !== null ? rows[focused.rowIdx]?.group : undefined}
              />
            </div>

            {/* ------------------------------------------------- right: the grid */}
            <div className="col-span-8 flex flex-col overflow-hidden">
              <StatusBar
                onRetry={() => lastFile.current && handleFile(lastFile.current)}
                extraction={extraction}
                mismatchCount={mismatchCount}
                blankCount={blankCount}
                uncheckedCount={uncheckedCount}
                rowCount={rows.length}
              />

              {extraction.spreadsheet && extraction.spreadsheet.unmapped_columns.length > 0 && (
                <UnmappedColumns
                  columns={extraction.spreadsheet.unmapped_columns}
                  categories={categories}
                  onMap={(header, key) => remapSpreadsheetColumn(header, key)}
                />
              )}

              <HeaderPanel
                headers={headers}
                onChange={(field, value) => setHeaders((h) => ({ ...h, [field]: value }))}
                open={showHeader}
                onToggle={() => setShowHeader((v) => !v)}
              />

              <div className="flex-1 overflow-auto pr-4 py-3">
                <table className="min-w-full text-xs border-collapse">
                  <thead className="sticky top-0 bg-white z-10">
                    {/*
                      Every heading on one line, in the same style. They used
                      to wrap wherever the column happened to be narrow, so
                      "Count / Size", "Rotten Spot" and "Stem Crack" broke
                      over two lines while "Sound" did not.
                    */}
                    <tr className="border-b-2 border-gray-300 text-gray-600">
                      <th className="w-9 min-w-9 sticky left-0 z-10 bg-white" />
                      <th className="py-2 px-2 text-left font-semibold whitespace-nowrap sticky left-9 z-10 bg-white">
                        {columnTitle(extraction.table.grouping_label)}
                      </th>
                      {categories.map((cat) => (
                        <th key={cat.key} className="py-2 px-1 font-semibold whitespace-nowrap">
                          <span className="inline-flex items-center justify-end gap-1 w-full">
                            <span
                              title={
                                cat.role === 'extra'
                                  ? 'Not one of the usual columns for this fruit — read from the sheet or added here'
                                  : undefined
                              }
                            >
                              {columnTitle(cat.label)}
                              {cat.role === 'extra' && <span className="text-blue-500">*</span>}
                            </span>
                            <button
                              onClick={() => removeColumn(cat.key)}
                              className="text-gray-300 hover:text-red-500"
                              title={`Remove the ${columnTitle(cat.label)} column`}
                            >
                              <X className="w-3 h-3" />
                            </button>
                          </span>
                        </th>
                      ))}
                      <th className="py-2 px-1 w-8 align-bottom">
                        {addingColumn ? (
                          <input
                            autoFocus
                            value={newColumn}
                            placeholder="Column name"
                            onChange={(e) => setNewColumn(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') addColumn(newColumn);
                              if (e.key === 'Escape') {
                                setAddingColumn(false);
                                setNewColumn('');
                              }
                            }}
                            onBlur={() => newColumn.trim() ? addColumn(newColumn) : setAddingColumn(false)}
                            className="w-28 px-1.5 py-1 border border-blue-400 rounded text-xs font-normal outline-none focus:ring-1 focus:ring-blue-500"
                          />
                        ) : (
                          <button
                            onClick={() => setAddingColumn(true)}
                            className="p-1 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded"
                            title="Add a defect column this sheet has and the list does not"
                          >
                            <Plus className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </th>
                      <th className="py-2 px-2 text-right font-semibold text-slate-700 bg-slate-100 whitespace-nowrap">
                        Written Total
                      </th>
                      <th className="py-2 px-2 text-right font-semibold text-blue-800 bg-blue-50 whitespace-nowrap">
                        Cells Add To
                      </th>
                      <th className="py-2 px-2 text-center font-semibold whitespace-nowrap">Check</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row, rIdx) => {
                      const chk = checks[rIdx];
                      // Subtotal lines are the ones with a written total, so
                      // they are the ones the arithmetic can actually check.
                      // They are set apart the way the surveyor sets them apart
                      // on the sheet, with the highlighter.
                      const rowTint =
                        chk.status === 'MISMATCH'
                          ? 'bg-red-50'
                          : chk.hasBlank
                          ? 'bg-amber-50/60'
                          : row.is_subtotal
                          ? 'bg-lime-50/70'
                          : '';
                      return (
                        <tr
                          key={rIdx}
                          className={`border-b border-gray-100 ${rowTint} ${
                            row.is_subtotal ? 'font-semibold border-t-2 border-t-lime-300' : ''
                          } hover:bg-slate-50/80`}
                        >
                          {/* First in the row so it is always in view; at the far right
                              it scrolled out of sight on a wide sheet. */}
                          <td className="w-9 min-w-9 py-1 pl-1 text-center sticky left-0 z-10 bg-white">
                            <button
                              onClick={() => deleteRow(rIdx)}
                              className="text-gray-400 hover:text-red-500 p-1 transition"
                              title="Remove this row"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </td>
                          <td className="py-1 px-2 sticky left-9 z-10 bg-white">
                            <input
                              type="text"
                              value={row.group}
                              placeholder="e.g. 30 XF"
                              onChange={(e) => setGroup(rIdx, e.target.value)}
                              className="w-24 px-1.5 py-1 border border-gray-200 rounded text-xs font-medium focus:ring-1 focus:ring-blue-500 outline-none"
                            />
                          </td>

                          {categories.map((cat) => {
                            const detail = row.cell_details?.[cat.key];
                            const val = row.values[cat.key];
                            const isFocused =
                              focused?.rowIdx === rIdx && focused?.catKey === cat.key;
                            const disagreed = detail?.agreement === 'DISAGREED';
                            const needsReview =
                              detail?.review_status === 'NEEDS_REVIEW' || val === null;

                            return (
                              <td key={cat.key} className="py-1 px-0.5 text-right relative">
                                <input
                                  type="number"
                                  min={0}
                                  step={isKg ? 0.001 : 1}
                                  value={val ?? ''}
                                  placeholder="?"
                                  onFocus={() => setFocused({ rowIdx: rIdx, catKey: cat.key })}
                                  onChange={(e) => setCell(rIdx, cat.key, e.target.value)}
                                  className={[
                                    'w-full min-w-[3rem] text-right px-1 py-1 rounded text-xs font-mono border outline-none transition',
                                    isFocused
                                      ? 'ring-2 ring-blue-500 border-blue-500'
                                      : disagreed
                                      ? 'border-purple-400 bg-purple-50 text-purple-900 font-bold'
                                      : needsReview
                                      ? 'border-amber-400 bg-amber-50 text-amber-900'
                                      : 'border-gray-200',
                                  ].join(' ')}
                                />
                                {disagreed && (
                                  <span
                                    className="absolute -bottom-0.5 right-1 text-[9px] text-purple-600 font-mono pointer-events-none"
                                    title="The two readers disagreed on this cell"
                                  >
                                    ≠{detail?.assist_value}
                                  </span>
                                )}
                              </td>
                            );
                          })}

                          <td className="w-8" />

                          {/* What the surveyor wrote at the end of the row */}
                          <td className="py-1 px-0.5 bg-slate-50">
                            <input
                              type="number"
                              min={0}
                              step={isKg ? 0.001 : 1}
                              value={row.stated_total ?? ''}
                              placeholder="—"
                              onChange={(e) => setStatedTotal(rIdx, e.target.value)}
                              className="w-full text-right px-1 py-1 border border-slate-300 rounded text-xs font-mono font-semibold outline-none focus:ring-1 focus:ring-slate-500"
                            />
                          </td>

                          {/* Derived, never typed over */}
                          <td className="py-1 px-2 text-right font-mono font-bold text-blue-900 bg-blue-50/50 select-none">
                            {fmt(chk.computed)}
                          </td>

                          <td className="py-1 px-1">
                            <RowCheckChip status={chk.status} delta={chk.delta} fmt={fmt} />
                          </td>

                        </tr>
                      );
                    })}
                  </tbody>
                  <tfoot>
                    <tr className="bg-gray-100 font-bold text-gray-900 border-t-2 border-gray-300">
                      <td className="sticky left-0 z-10 bg-gray-100" />
                      <td className="py-2 px-2 text-xs whitespace-nowrap sticky left-9 z-10 bg-gray-100">All boxes</td>
                      {categories.map((cat) => (
                        <td key={cat.key} className="py-2 px-1 text-right font-mono text-xs">
                          {fmt(columnTotals[cat.key])}
                        </td>
                      ))}
                      <td className="w-8" />
                      <td className="bg-slate-100" />
                      <td className="py-2 px-2 text-right font-mono text-xs bg-blue-100/60 text-blue-950">
                        {fmt(grandTotal)}
                      </td>
                      <td />
                    </tr>
                    {sheetTotals && (
                      // The sheet's own "Total" line. Shown for comparison only;
                      // it is not a sample box and is never saved as one.
                      <tr className="text-gray-600 border-t border-gray-200">
                        <td className="sticky left-0 z-10 bg-white" />
                        <td
                          className="py-1.5 px-2 text-[11px] whitespace-nowrap sticky left-9 z-10 bg-white italic"
                          title="The Total line written at the foot of the sheet"
                        >
                          Written on sheet
                        </td>
                        {categories.map((cat) => {
                          const w = sheetTotals.values?.[cat.key];
                          const has = typeof w === 'number';
                          const off = has && toUnits(w as number) !== toUnits(columnTotals[cat.key]);
                          return (
                            <td
                              key={cat.key}
                              className={`py-1.5 px-1 text-right font-mono text-[11px] ${off ? 'text-red-700 font-bold' : ''}`}
                              title={off ? 'Does not match the column added up above' : undefined}
                            >
                              {has ? fmt(w as number) : ''}
                            </td>
                          );
                        })}
                        <td className="w-8" />
                        <td className="bg-slate-50" />
                        <td
                          className={`py-1.5 px-2 text-right font-mono text-[11px] ${
                            typeof sheetTotals.stated_total === 'number' &&
                            toUnits(sheetTotals.stated_total) !== toUnits(grandTotal)
                              ? 'text-red-700 font-bold'
                              : ''
                          }`}
                        >
                          {typeof sheetTotals.stated_total === 'number' ? fmt(sheetTotals.stated_total) : ''}
                        </td>
                        <td />
                      </tr>
                    )}
                  </tfoot>
                </table>

                <button
                  onClick={addRow}
                  className="mt-3 ml-4 inline-flex items-center gap-1.5 text-xs font-medium text-blue-700 hover:text-blue-900 hover:bg-blue-50 px-2.5 py-1.5 rounded transition"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Add a sample box
                </button>

                <p className="mt-2 pl-4 text-[11px] text-gray-400">
                  One row per sample box opened. Several boxes of the same count are normal —
                  they are aggregated in the report, not merged here.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------ footer */}
        <div className="flex items-center justify-between px-5 py-3 border-t border-gray-200 bg-gray-50">
          <div className="text-xs text-gray-500">
            {extraction && mismatchCount > 0 && (
              <span className="text-red-700 font-semibold">
                {mismatchCount} row{mismatchCount > 1 ? 's do' : ' does'} not add up to the written
                total — fix before saving.
              </span>
            )}
            {extraction && mismatchCount === 0 && blankCount > 0 && (
              <span className="text-amber-700 font-medium">
                {blankCount} row{blankCount > 1 ? 's have' : ' has'} a cell that could not be read.
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-200 rounded-lg transition"
            >
              Cancel
            </button>
            {extraction && (
              <button
                onClick={handleApply}
                disabled={applying || mismatchCount > 0 || rows.length === 0}
                className="inline-flex items-center gap-2 px-5 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-lg transition"
                title={
                  mismatchCount > 0
                    ? 'Rows that do not add up cannot be saved'
                    : 'Save these figures into the report'
                }
              >
                {applying ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Saving…
                  </>
                ) : (
                  <>
                    Save to report
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

/* ========================================================================== */
/* Sub-components                                                             */
/* ========================================================================== */

/**
 * The photograph: zoom, drag to move around, and a highlight on the cell in hand.
 *
 * Zoom applies whether or not a cell carries a crop box. It used to apply only
 * when one did, and the cloud reader reads the page whole rather than cell by
 * cell, so it returns no boxes — which meant the zoom buttons moved the number
 * on screen and did nothing else. Since the surveyor is reading handwriting off
 * a phone photo, being able to magnify and move around it is the point.
 *
 * When the focused cell does have a box, the view centres on it automatically
 * and any manual panning is set aside, so clicking through cells walks the photo
 * for him.
 */
const SheetPane: React.FC<{
  src: string;
  box?: [number, number, number, number];
  zoom: number;
  hasFocus: boolean;
}> = ({ src, box, zoom, hasFocus }) => {
  const [pan, setPan] = React.useState({ x: 0, y: 0 });
  const drag = React.useRef<{ x: number; y: number; panX: number; panY: number } | null>(null);

  const centred = Boolean(box) && hasFocus;

  // Nothing to pan at 1x, so the offset is dropped rather than left stale.
  React.useEffect(() => {
    if (zoom <= 1) setPan({ x: 0, y: 0 });
  }, [zoom]);

  // The focused cell wins over wherever the surveyor had dragged to.
  React.useEffect(() => {
    if (centred) setPan({ x: 0, y: 0 });
  }, [centred, box?.[0], box?.[1]]);

  if (!src) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-400 text-xs px-6 text-center">
        No sheet image — figures are being typed by hand.
      </div>
    );
  }

  const cx = box ? (box[0] + box[2]) / 2 : 0.5;
  const cy = box ? (box[1] + box[3]) / 2 : 0.5;
  const offsetX = centred ? (0.5 - cx) * 100 : 0;
  const offsetY = centred ? (0.5 - cy) * 100 : 0;

  const onPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (zoom <= 1) return;
    (e.target as Element).setPointerCapture?.(e.pointerId);
    drag.current = { x: e.clientX, y: e.clientY, panX: pan.x, panY: pan.y };
  };

  const onPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!drag.current) return;
    setPan({
      x: drag.current.panX + (e.clientX - drag.current.x),
      y: drag.current.panY + (e.clientY - drag.current.y),
    });
  };

  const endDrag = () => {
    drag.current = null;
  };

  return (
    <div
      className="flex-1 overflow-hidden relative bg-slate-200"
      style={{ cursor: zoom > 1 ? (drag.current ? 'grabbing' : 'grab') : 'default' }}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={endDrag}
      onPointerLeave={endDrag}
    >
      <div
        className={`absolute inset-0 ${drag.current ? '' : 'transition-transform duration-200 ease-out'}`}
        style={{
          transform:
            `translate(${pan.x}px, ${pan.y}px) ` +
            `scale(${zoom}) ` +
            `translate(${offsetX}%, ${offsetY}%)`,
          transformOrigin: 'center center',
        }}
      >
        <img
          src={src}
          alt="Tally sheet"
          draggable={false}
          className="w-full h-full object-contain select-none"
        />
        {box && (
          <div
            className="absolute border-2 border-blue-500 bg-blue-400/20 rounded-sm pointer-events-none shadow-[0_0_0_9999px_rgba(15,23,42,0.35)]"
            style={{
              left: `${box[0] * 100}%`,
              top: `${box[1] * 100}%`,
              width: `${(box[2] - box[0]) * 100}%`,
              height: `${(box[3] - box[1]) * 100}%`,
            }}
          />
        )}
      </div>
      {/*
        No box means the page was read whole rather than cell by cell, so there
        is no rectangle to point at. Saying which row and column is in hand and
        inviting the surveyor to zoom is more use than an apology.
      */}
      {!box && hasFocus && (
        <div className="absolute bottom-2 left-2 right-2 text-[11px] text-slate-700 bg-white/90 rounded px-2 py-1">
          {zoom > 1
            ? 'Drag the sheet to move around it.'
            : 'Zoom in with + to read the handwriting, then drag to move around.'}
        </div>
      )}
    </div>
  );
};

/** The cropped handwriting the focused number came from. */
const CellInspector: React.FC<{
  detail?: any;
  label?: string;
  rowLabel?: string;
}> = ({ detail, label, rowLabel }) => {
  if (!label) {
    return (
      <div className="border-t border-gray-200 bg-white px-3 py-2.5 text-[11px] text-gray-400 h-[88px] flex items-center">
        Click a cell to see the handwriting it was read from.
      </div>
    );
  }

  return (
    <div className="border-t border-gray-200 bg-white px-3 py-2.5 h-[88px]">
      <div className="text-[11px] font-semibold text-gray-700 mb-1.5 truncate">
        {rowLabel || 'Row'} → {label}
      </div>
      <div className="flex items-center gap-3">
        {detail?.cell_image ? (
          <img
            src={detail.cell_image}
            alt="Handwriting"
            className="h-10 max-w-[110px] object-contain border border-gray-200 rounded bg-white"
          />
        ) : (
          <span className="text-[11px] text-gray-400 italic">
            Read from the whole page — use the sheet on the left.
          </span>
        )}
        <div className="text-[11px] text-gray-600 space-y-0.5 min-w-0">
          {detail?.raw_text ? (
            <div className="truncate">
              Read as <code className="bg-gray-100 px-1 rounded font-mono">{detail.raw_text}</code>
            </div>
          ) : null}
          {typeof detail?.confidence === 'number' && detail.confidence > 0 && (
            <div>
              Confidence{' '}
              <span
                className={
                  detail.confidence >= 0.85 ? 'text-emerald-700 font-semibold' : 'text-amber-700 font-semibold'
                }
              >
                {Math.round(detail.confidence * 100)}%
              </span>
            </div>
          )}
          {detail?.agreement === 'DISAGREED' && (
            <div className="text-purple-700 font-medium">
              Second reader made it {detail.assist_value}
            </div>
          )}
          {detail?.agreement === 'AGREED' && (
            <div className="text-emerald-700">Both readers agree</div>
          )}
          {detail?.validation?.message && (
            <div className="text-amber-700 truncate" title={detail.validation.message}>
              {detail.validation.message}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

/**
 * The header block off the sheet: party, container, dates, room, readings.
 *
 * Read as a separate set from the counts, because it is separate on the sheet
 * and it goes somewhere else in the report — the particulars table and the
 * measurements table, not the defect grid.
 *
 * Unlike the counts, none of this can be proved by arithmetic. There is no
 * total to check a container number against. So these fields are laid out to be
 * read against the sheet rather than trusted: six or seven values, a few
 * seconds, and they carry straight into the report once confirmed.
 */
const HEADER_FIELDS: Array<{ key: string; label: string; type: 'text' | 'date' | 'number' }> = [
  { key: 'party_name', label: 'Party / Consignee', type: 'text' },
  { key: 'container_number', label: 'Container No.', type: 'text' },
  { key: 'survey_date', label: 'Survey date', type: 'date' },
  { key: 'destuff_date', label: 'Destuff date', type: 'date' },
  { key: 'room_no', label: 'Cold room', type: 'text' },
  { key: 'room_temp', label: 'Room temp °C', type: 'number' },
];

const HEADER_RANGES: Array<{ min: string; max: string; label: string }> = [
  { min: 'pulp_temp_min', max: 'pulp_temp_max', label: 'Pulp temp °C' },
  { min: 'brix_min', max: 'brix_max', label: 'Brix %' },
  { min: 'pressure_min', max: 'pressure_max', label: 'Pressure' },
];

/**
 * Spreadsheet columns that matched nothing.
 *
 * The cold store names its columns whatever it likes, and the old import wrote
 * a zero wherever a name did not line up — a zero being a real count of nothing
 * that shifts every percentage in the finished report. So an unmatched column
 * stops here and waits for the surveyor: put it somewhere, or say it is not a
 * defect count. Nothing is assumed either way.
 */
const UnmappedColumns: React.FC<{
  columns: string[];
  categories: TallyCategory[];
  onMap: (header: string, key: string) => void;
}> = ({ columns, categories, onMap }) => (
  <div className="border-b border-amber-200 bg-amber-50 px-4 py-2.5">
    <div className="flex items-start gap-2 text-xs text-amber-900">
      <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
      <div className="flex-1">
        <p className="font-semibold">
          {columns.length} column{columns.length > 1 ? 's' : ''} in this spreadsheet
          {columns.length > 1 ? ' do' : ' does'} not match any of the report's columns.
        </p>
        <p className="text-amber-800 mt-0.5">
          Say where each belongs, or drop it. Until then its figures are not in the grid.
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          {columns.map((header) => (
            <div
              key={header}
              className="flex items-center gap-1.5 bg-white border border-amber-300 rounded px-2 py-1"
            >
              <span className="font-mono text-[11px] text-gray-800">{header}</span>
              <span className="text-amber-500">→</span>
              <select
                defaultValue=""
                onChange={(e) => e.target.value && onMap(header, e.target.value)}
                className="text-[11px] border border-gray-300 rounded px-1 py-0.5 outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="" disabled>
                  choose…
                </option>
                {categories.map((c) => (
                  <option key={c.key} value={c.key}>
                    {c.label}
                  </option>
                ))}
                <option value="DROP">— not a defect count —</option>
              </select>
            </div>
          ))}
        </div>
      </div>
    </div>
  </div>
);

const HeaderPanel: React.FC<{
  headers: Record<string, any>;
  onChange: (field: string, value: any) => void;
  open: boolean;
  onToggle: () => void;
}> = ({ headers, onChange, open, onToggle }) => {
  const filled = [...HEADER_FIELDS.map((f) => f.key), ...HEADER_RANGES.map((r) => r.min)].filter(
    (k) => headers[k] !== null && headers[k] !== undefined && headers[k] !== '',
  ).length;

  return (
    <div className="border-b border-gray-200 bg-slate-50/70">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-4 py-2 text-xs hover:bg-slate-100 transition"
      >
        <span className="font-semibold text-gray-700">
          Details from the top of the sheet
          <span className="ml-2 font-normal text-gray-500">
            {filled} of {HEADER_FIELDS.length + HEADER_RANGES.length} read — check against the sheet
          </span>
        </span>
        <span className="text-gray-400">{open ? '▾' : '▸'}</span>
      </button>

      {open && (
        <div className="px-4 pb-3 grid grid-cols-3 gap-x-3 gap-y-2">
          {HEADER_FIELDS.map((f) => (
            <label key={f.key} className="block">
              <span className="block text-[10px] font-medium text-gray-500 mb-0.5">{f.label}</span>
              <input
                type={f.type === 'number' ? 'number' : f.type}
                step={f.type === 'number' ? '0.01' : undefined}
                value={headers[f.key] ?? ''}
                placeholder="—"
                onChange={(e) =>
                  onChange(
                    f.key,
                    f.type === 'number'
                      ? (e.target.value === '' ? null : Number(e.target.value))
                      : e.target.value,
                  )
                }
                className={`w-full px-1.5 py-1 border rounded text-xs outline-none focus:ring-1 focus:ring-blue-500 ${
                  headers[f.key] ? 'border-gray-300 bg-white' : 'border-amber-300 bg-amber-50/50'
                }`}
              />
            </label>
          ))}

          {HEADER_RANGES.map((r) => (
            <label key={r.min} className="block">
              <span className="block text-[10px] font-medium text-gray-500 mb-0.5">{r.label}</span>
              <div className="flex gap-1">
                {[r.min, r.max].map((k, i) => (
                  <input
                    key={k}
                    type="number"
                    step="0.01"
                    value={headers[k] ?? ''}
                    placeholder={i === 0 ? 'min' : 'max'}
                    onChange={(e) => onChange(k, e.target.value === '' ? null : Number(e.target.value))}
                    className={`w-1/2 px-1.5 py-1 border rounded text-xs outline-none focus:ring-1 focus:ring-blue-500 ${
                      headers[k] !== null && headers[k] !== undefined
                        ? 'border-gray-300 bg-white'
                        : 'border-amber-300 bg-amber-50/50'
                    }`}
                  />
                ))}
              </div>
            </label>
          ))}
        </div>
      )}
    </div>
  );
};

/** Green / red / grey — three states, because unchecked is not the same as passed. */
const RowCheckChip: React.FC<{
  status: 'OK' | 'MISMATCH' | 'UNCHECKED';
  delta: number | null;
  fmt?: (v: number) => string;
}> = ({ status, delta, fmt = String }) => {
  if (status === 'OK') {
    return (
      <span className="inline-flex items-center gap-1 whitespace-nowrap text-[11px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded">
        <Check className="w-3 h-3" /> Ties out
      </span>
    );
  }
  if (status === 'MISMATCH') {
    return (
      <span
        className="inline-flex items-center gap-1 whitespace-nowrap text-[11px] font-bold text-red-700 bg-red-100 border border-red-300 px-1.5 py-0.5 rounded"
        title="The cells and the written total disagree"
      >
        <AlertTriangle className="w-3 h-3" />
        {delta !== null && (delta > 0 ? `+${fmt(delta)}` : fmt(delta))}
      </span>
    );
  }
  return (
    <span
      className="inline-flex items-center gap-1 whitespace-nowrap text-[11px] text-gray-500 bg-gray-100 border border-gray-200 px-1.5 py-0.5 rounded"
      title="No total was written on this row, so there is nothing to check against"
    >
      <Minus className="w-3 h-3" /> No total
    </span>
  );
};

/** Says plainly what happened, including when nothing could be read. */
const StatusBar: React.FC<{
  extraction: TallyExtraction;
  mismatchCount: number;
  blankCount: number;
  uncheckedCount: number;
  rowCount: number;
  onRetry?: () => void;
}> = ({ extraction, mismatchCount, blankCount, uncheckedCount, rowCount, onRetry }) => {
  const reader = extraction.reader;

  // Nothing read is never green. The demo screen showed "All 0 rows checked"
  // in green when the online reader was down and nothing had been read at all.
  const tone =
    mismatchCount > 0
      ? 'bg-red-50 border-red-200 text-red-900'
      : blankCount > 0 || rowCount === 0
      ? 'bg-amber-50 border-amber-200 text-amber-900'
      : 'bg-emerald-50 border-emerald-200 text-emerald-900';

  let headline: string;
  if (rowCount === 0 && reader?.cloud_error && extraction.filename !== 'Typed by hand') {
    headline = `Nothing was read from this photo. ${reader.cloud_error}`;
  } else if (rowCount === 0 && extraction.spreadsheet) {
    headline =
      'No rows came through from this spreadsheet. Map the columns above, or use "Add a sample box" to type the rows in.';
  } else if (rowCount === 0 && extraction.filename !== 'Typed by hand') {
    headline =
      'Nothing could be read from this photo. Press Change to try again, or use "Add a sample box" to type the rows in.';
  } else if (extraction.extraction_status === 'NO_ENGINE') {
    headline =
      'No handwriting reader is installed on this server, so nothing was read from the photo. Type the figures in — the row checks still work.';
  } else if (extraction.extraction_status === 'NO_GRID') {
    headline =
      rowCount > 0
        ? 'Figures are being entered by hand.'
        : 'The ruled grid could not be found on this photo — the lines may be too faint. Add the rows by hand; the sheet stays on the left to read from.';
  } else if (mismatchCount > 0) {
    headline = `${mismatchCount} row${mismatchCount > 1 ? 's' : ''} disagree with the written total.`;
  } else if (blankCount > 0) {
    headline = `${blankCount} row${blankCount > 1 ? 's' : ''} still have a cell that could not be read.`;
  } else {
    headline = `All ${rowCount} rows checked.`;
  }

  return (
    <div className={`px-4 py-2 border-b ${tone} text-xs`}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <Info className="w-3.5 h-3.5 shrink-0" />
          <span className="font-medium">{headline}</span>
          {rowCount === 0 && onRetry && extraction.filename !== 'Typed by hand' && (
            <button
              onClick={onRetry}
              className="shrink-0 ml-1 px-2.5 py-1 bg-white border border-amber-400 text-amber-900 rounded font-semibold hover:bg-amber-100"
            >
              Try again
            </button>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0 text-[11px]">
          {uncheckedCount > 0 && (
            <span className="text-gray-600 bg-white/70 px-1.5 py-0.5 rounded border border-gray-200">
              {uncheckedCount} without a written total
            </span>
          )}
          {reader?.used === 'cloud' && (
            <span className="bg-blue-50 text-blue-800 px-1.5 py-0.5 rounded border border-blue-200">
              Read online{reader.header_sent === false ? ' (header not sent)' : ''}
            </span>
          )}
          {reader?.used === 'local' && extraction.ocr_engine && (
            <span className="bg-white/70 px-1.5 py-0.5 rounded border border-gray-200 text-gray-700">
              Read on this server by {extraction.ocr_engine}
            </span>
          )}
          {reader?.used === 'local' && reader.cloud_error && rowCount > 0 && (
            <span
              className="bg-white/70 px-1.5 py-0.5 rounded border border-gray-200 text-gray-600 max-w-[280px] truncate"
              title={reader.cloud_error}
            >
              {reader.cloud_error}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

/** First screen: what this deployment can do, and the upload box. */
const UploadPane: React.FC<{
  caps: TallyCapabilities | null;
  loading: boolean;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  onFile: (f: File) => void;
  onStartBlank: () => void;
  sourceHint: 'any' | 'spreadsheet';
  existingCount: number;
  onEditExisting: () => void;
}> = ({ caps, loading, fileInputRef, onFile, onStartBlank, sourceHint, existingCount, onEditExisting }) => {
  const sheetOnly = sourceHint === 'spreadsheet';
  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-3">
        <Loader2 className="w-9 h-9 text-blue-600 animate-spin" />
        <p className="text-sm font-medium text-gray-700">Reading the file…</p>
        <p className="text-xs text-gray-500">This can take up to a minute for a photo</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-2xl mx-auto space-y-4">
        {existingCount > 0 && (
          <button
            onClick={onEditExisting}
            className="w-full flex items-center justify-between gap-3 p-4 bg-emerald-50 border border-emerald-300 rounded-xl text-left hover:bg-emerald-100 transition"
          >
            <span>
              <span className="block text-sm font-semibold text-emerald-900">
                Edit the figures already in the report
              </span>
              <span className="block text-xs text-emerald-800 mt-0.5">
                {existingCount} row{existingCount > 1 ? 's' : ''} saved. Open them, correct them, and save again.
              </span>
            </span>
            <ArrowRight className="w-4 h-4 text-emerald-700 shrink-0" />
          </button>
        )}
        <div
          className="border-2 border-dashed border-gray-300 rounded-2xl p-10 text-center hover:border-blue-500 hover:bg-blue-50/30 transition cursor-pointer"
          onClick={() => fileInputRef.current?.click()}
          onDrop={(e) => {
            e.preventDefault();
            const f = e.dataTransfer.files?.[0];
            if (f) onFile(f);
          }}
          onDragOver={(e) => e.preventDefault()}
        >
          <div className="w-14 h-14 mx-auto bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mb-3">
            <Upload className="w-7 h-7" />
          </div>
          <h3 className="text-base font-semibold text-gray-800">
            {sheetOnly ? 'Upload the CSV or Excel file' : 'Upload the tally sheet — photo or Excel'}
          </h3>
          <p className="text-xs text-gray-500 mt-1">
            {sheetOnly
              ? 'The spreadsheet from the cold store. Columns that do not match are shown for you to map.'
              : 'The photo of the notebook page, or the CSV / Excel file from the cold store. Drop it here or click to browse.'}
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept={sheetOnly ? '.csv,.xlsx,.xlsm,.xls' : 'image/*,.csv,.xlsx,.xlsm,.xls'}
            className="hidden"
            onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
          />
        </div>

        {caps && (
          <div className="border border-gray-200 rounded-xl p-4 bg-gray-50/60 space-y-3 text-xs">
            <div className="flex items-start justify-between gap-4">
              <div>
                <span className="font-semibold text-gray-700">Columns for this report</span>
                <p className="text-gray-500 mt-0.5">
                  {caps.commodity
                    ? `Set by the commodity (${caps.commodity.toLowerCase()}), counted in ${caps.unit}.`
                    : 'No commodity chosen yet, so only Sound is set up. Pick one on the report to get the rest.'}
                </p>
              </div>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {caps.categories.map((c) => (
                <span
                  key={c.key}
                  className="px-2 py-0.5 bg-white border border-gray-200 rounded text-gray-700"
                >
                  {c.label}
                </span>
              ))}
            </div>

            {caps.reader === 'cloud' && (
              <div className="flex items-start gap-2 p-2.5 bg-blue-50 border border-blue-200 rounded-lg text-blue-900">
                <CloudUpload className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                <span>
                  <span className="font-semibold">The sheet is read online.</span>{' '}
                  {caps.cloud_sends_header
                    ? 'The whole page is sent, so the party name, container number, dates and readings at the top are filled in too.'
                    : 'Only the number grid is sent — the top of the sheet stays here, so the party name and container number are typed in by hand.'}{' '}
                  Everything that comes back is a draft until you have checked it.
                </span>
              </div>
            )}

            {caps.reader === 'local' && (
              <div className="flex items-start gap-2 p-2.5 bg-amber-50 border border-amber-200 rounded-lg text-amber-900">
                <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                <span>
                  Reading happens on this server ({caps.ocr_engines.join(', ')}), which does not cope
                  with a sideways photo or highlighter across a row. Expect to fill in a fair
                  amount by hand. Setting an online reader key makes this much better.
                </span>
              </div>
            )}

            {caps.reader === 'none' && (
              <div className="flex items-start gap-2 p-2.5 bg-amber-50 border border-amber-200 rounded-lg text-amber-900">
                <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                <span>
                  Nothing on this server can read handwriting, so an uploaded photo will not be read
                  automatically. The workbench still works: the sheet shows on the left and the row
                  checks run as you type.
                </span>
              </div>
            )}
          </div>
        )}

        <div className="text-center">
          <button
            onClick={onStartBlank}
            className="text-xs text-gray-500 hover:text-gray-800 underline underline-offset-2"
          >
            Skip the photo and type the figures in
          </button>
        </div>
      </div>
    </div>
  );
};

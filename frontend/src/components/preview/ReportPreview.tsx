import React, { useState, useMemo, useRef, useLayoutEffect } from 'react';
import {
  Printer,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Download,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  FileText,
} from 'lucide-react';
import { computeBlockState } from './compute';
import { PageContainer } from './PageContainer';
import {
  ParticularsBlock,
  NarrativeBlock,
  MeasurementsBlock,
  TableBlock,
  PhotoPlateBlock,
  FixedTextBlock,
  PartiesBlock,
  AttendanceBlock,
  TimelineBlock,
  ReconciliationBlock,
  InventoryBlock,
  AnnexuresBlock,
  UnitGroupBlock,
  RecordersBlock,
} from './blocks';
import { getDownloadDocxUrl, getDownloadPdfUrl, getPreviewHtmlUrl } from '../../api/client';
import { previewPhotos, PreviewPhoto } from './blocks/PhotoPlateBlock';
import { SurveyUnitBlock } from './blocks/SurveyUnitBlock';
import { GridTableBlock } from './blocks/GridTableBlock';
import { reportTable, weightSummary } from '../../utils/gcTables';
import { layoutOf, photoPages as photoPages_ } from '../../utils/photoLayout';
import { clauseContextFrom, detectCauseCondition } from '../../utils/clauseContext';
import { CURATED_FRUITS, HouseStyleContext, PHOTOS_HEADING, Piece, autoMarks, isSurveyReport, narrativePieces, reportTitle, splitNarrative } from '../../utils/houseStyle';

export interface ReportPreviewProps {
  report?: any;
  blockState: any;
  reportNumber?: string;
  onBackToEdit?: () => void;
  onBlockChange?: (updatedBlock: any) => void;
  onBlockStateChange?: (updatedState: any) => void;
  editable?: boolean;
  /**
   * Runs before a download. Downloads are built from what the server holds, so
   * unsaved edits have to be saved first or the file comes out stale. Return
   * false to cancel.
   */
  beforeDownload?: () => Promise<boolean>;
}

export const ReportPreview: React.FC<ReportPreviewProps> = ({
  report,
  blockState,
  reportNumber,
  onBackToEdit,
  onBlockChange,
  onBlockStateChange,
  editable = true,
  beforeDownload,
}) => {
  const [zoom, setZoom] = useState<number>(100);
  const [viewMode, setViewMode] = useState<'paginated' | 'all'>('all');
  const [currentPage, setCurrentPage] = useState<number>(1);

  // Compute block state with pure zero-drift logic
  const computedState = useMemo(() => {
    return computeBlockState(blockState);
  }, [blockState]);

  // Unticked sections are left out here exactly as they are in the Word/PDF.
  const blocks: any[] = (computedState?.blocks || []).filter((b: any) => b?.included !== false);
  const metadata = computedState?.metadata || report?.block_state?.metadata || {};
  const repNum = reportNumber || report?.report_number || metadata?.number || 'QC-DRAFT';
  // Running header as in the client's reports: "FINAL SURVEY REPORT NO. M-…".
  const isQc = (metadata?.family || report?.family) === 'QC_REPORT';
  const stage = String(metadata?.state || report?.state || 'FINAL').toUpperCase() === 'PRELIMINARY' ? 'PRELIMINARY' : 'FINAL';
  const headerLabel = `${stage} SURVEY REPORT`;
  // Survey reports print in the client's look (border, banner, Arial, blue headings).
  const house = !isQc && isSurveyReport(metadata, report);
  const assets = computedState?.assets || {};
  const clauseContext = useMemo(() => clauseContextFrom(blockState), [blockState]);

  // Separate blocks for realistic pagination:
  // Page 1: Overview & Survey Data
  // Page 2+: Evidence (photos), Documentation (annexures), Legal (fixed_text)
  // General cargo: the WEIGHT FINAL SUMMARY follows the last survey paragraph.
  const lastUnitId = [...blocks].reverse().find((b) => b.type === 'survey_unit')?.id;
  const page1Blocks = blocks.filter((b) =>
    ['parties', 'attendance', 'particulars', 'timeline', 'narrative', 'measurements', 'table', 'reconciliation', 'inventory', 'unit_group', 'temperature_recorders', 'survey_unit', 'gc_table'].includes(b.type)
  );
  const photoBlocks = blocks.filter((b) => b.type === 'photo_plate');
  const fixedTextBlocks = blocks.filter((b) => b.type === 'fixed_text');
  const annexureBlocks = blocks.filter((b) => b.type === 'annexures');

  // Photo pages, as many photos to a page as the photo section is set to
  // (8 or 6), the same split the Word file makes.
  const photoPages: Array<{ block: any; slice: PreviewPhoto[]; first: boolean }> = [];
  photoBlocks.forEach((pb) => {
    const lay = layoutOf(pb);
    photoPages_(previewPhotos(pb, assets, report?.id || blockState?.id), lay).forEach((slice, i) =>
      photoPages.push({ block: pb, slice, first: i === 0 }),
    );
  });

  // Calculate total pages
  let totalPages = 1; // Page 1
  if (photoPages.length > 0) {
    totalPages += photoPages.length;
  } else if (fixedTextBlocks.length > 0 && page1Blocks.length > 3) {
    totalPages += 1;
  }

  /** One section of the report; live=false renders it read-only (for measuring page breaks). */
  const renderBlock = (b: any, live = true): React.ReactNode => {
    if (b.type === 'parties') {
      return (
        <PartiesBlock
          key={b.id}
          block={b}
          onChange={live ? onBlockChange : undefined}
          editable={live && editable}
        />
      );
    }
    if (b.type === 'attendance') {
      return (
        <AttendanceBlock
          key={b.id}
          block={b}
          onChange={live ? onBlockChange : undefined}
          editable={live && editable}
        />
      );
    }
    if (b.type === 'particulars') {
      return (
        <ParticularsBlock
          key={b.id}
          block={b}
          onChange={live ? onBlockChange : undefined}
          editable={live && editable}
        />
      );
    }
    if (b.type === 'timeline') {
      return (
        <TimelineBlock
          key={b.id}
          block={b}
          onChange={live ? onBlockChange : undefined}
          editable={live && editable}
        />
      );
    }
    if (b.type === 'narrative') {
      const isCauseOfLoss =
        b.id === 'b_cause' ||
        b.section === 'cause_of_loss' ||
        /cause of loss/i.test(b.section || '');
      const recordersBlock = isCauseOfLoss ? blocks.find((other: any) => other.type === 'temperature_recorders') : undefined;

      return (
        <NarrativeBlock
          key={b.id}
          block={b}
          onChange={live ? onBlockChange : undefined}
          editable={live && editable}
          clauseContext={clauseContext}
          isFormEditor={false}
          recordersBlock={recordersBlock}
          onRecordersChange={live ? onBlockChange : undefined}
          reportId={report?.id}
        />
      );
    }
    if (b.type === 'measurements') {
      return (
        <MeasurementsBlock
          key={b.id}
          block={b}
          onChange={live ? onBlockChange : undefined}
          editable={live && editable}
        />
      );
    }
    if (b.type === 'table') {
      return (
        <TableBlock
          key={b.id}
          block={b}
          computed={b._computed}
          onChange={live ? onBlockChange : undefined}
          editable={live && editable}
        />
      );
    }
    if (b.type === 'reconciliation') {
      return <ReconciliationBlock key={b.id} block={b} />;
    }
    if (b.type === 'inventory') {
      return <InventoryBlock key={b.id} block={b} />;
    }
    if (b.type === 'unit_group') {
      return <UnitGroupBlock key={b.id} block={b} reportId={report?.id} />;
    }
    if (b.type === 'survey_unit') {
      return <SurveyUnitBlock key={b.id} block={b} summary={b.id === lastUnitId ? weightSummary(blocks) : null} />;
    }
    if (b.type === 'gc_table') {
      return <GridTableBlock key={b.id} table={reportTable(b)} testId={`gc-${b.kind}-table`} />;
    }
    if (b.type === 'temperature_recorders') {
      const hasCauseOfLoss = blocks.some(
        (other: any) => other.id === 'b_cause' || /cause of loss/i.test(other.section || '')
      );
      if (hasCauseOfLoss) {
        return null;
      }
      return <RecordersBlock key={b.id} block={b} reportId={report?.id} />;
    }
    return null;
  };

  // ---------------------------------------------------------------------------
  // Survey reports: real A4 pages, broken where the Word file breaks them.
  // Each section is cut into its printed pieces (heading, paragraphs and
  // lists, recorder tables, attendance; the cover table row by row); every
  // piece is measured off-screen and the pieces are packed into A4 pages. A
  // heading never ends a page. A section being edited is shown whole. The
  // photos follow straight on, a row of two at a time (as Word flows them),
  // under one "SURVEY PHOTOGRAPHS" heading, and the closing ends the report.
  // ---------------------------------------------------------------------------
  type FlowItem = { key: string; block?: any; piece?: Piece; row?: number; photos?: PreviewPhoto[]; keep?: boolean };
  const measureRef = useRef<HTMLDivElement | null>(null);
  const [heights, setHeights] = useState<Record<string, number>>({});
  const [editing, setEditing] = useState<{ id: string; field: 'additional_text' | 'preamble' } | null>(null);
  const closingInFlow = house && (fixedTextBlocks.length > 0 || annexureBlocks.length > 0);
  const recordersBlock = blocks.find((other: any) => other.type === 'temperature_recorders');
  const recCount = (recordersBlock?.recorders || []).filter((r: any) => r.included !== false).length;
  const fruitKey = String(clauseContext?.commodity || '').toLowerCase();
  const isCause = (b: any) => b.id === 'b_cause' || b.section === 'cause_of_loss' || /cause of loss/i.test(b.section || '');
  // Paragraph 3 of the 5 fruits carries the recorders, one piece each.
  const splitsCause = (b: any) => {
    if (!house || recCount === 0 || !isCause(b) || !CURATED_FRUITS.includes(fruitKey)) return false;
    const cond = b.cause_condition || (clauseContext ? detectCauseCondition(clauseContext, b) : 'no_recorder_data');
    return cond !== 'no_recorder_data';
  };
  const piecesOf = (b: any): Piece[] => {
    const hasPeople = (b.attendance || []).some((r: any) =>
      ['name', 'designation', 'representing'].some((k) => String(r?.[k] || '').trim())
    );
    const recs = splitsCause(b) ? recCount : 0;
    if (!String(b.additional_text || '').trim() && !String(b.preamble || '').trim() && !hasPeople && !recs) return [];
    const isApplication = b.id === 'b_para1' || /application/i.test(b.section || '');
    return narrativePieces(b, fruitKey, { heading: true, recorders: recs, attendance: isApplication && hasPeople });
  };
  const isSub = (b: any, pc: Piece) => {
    if (pc.kind !== 'text' && pc.kind !== 'pre') return pc.kind === 'heading';
    const src = pc.kind === 'text' ? b.additional_text : b.preamble;
    return splitNarrative(autoMarks(String(src || ''), fruitKey))[pc.part]?.kind === 'h';
  };
  const flow: FlowItem[] = [];
  if (house) {
    flow.push({ key: '__title', keep: true });
    for (const b of page1Blocks) {
      if (b.type === 'narrative' && editing?.id !== b.id) {
        piecesOf(b).forEach((pc, i) => flow.push({ key: `${b.id}::${i}`, block: b, piece: pc, keep: isSub(b, pc) }));
      } else if (b.type === 'particulars' && (b.rows || []).length > 1) {
        (b.rows || []).forEach((_: any, i: number) => flow.push({ key: `${b.id}::r${i}`, block: b, row: i }));
      } else {
        flow.push({ key: String(b.id), block: b });
      }
    }
    photoBlocks.forEach((pb) => {
      const photos = previewPhotos(pb, assets, report?.id || blockState?.id);
      if (photos.length && !flow.some((it) => it.key === '__photos_heading')) flow.push({ key: '__photos_heading', keep: true });
      for (let i = 0; i < photos.length; i += 2) flow.push({ key: `${pb.id}::p${i / 2}`, block: pb, photos: photos.slice(i, i + 2) });
    });
    if (closingInFlow) flow.push({ key: '__closing' });
  }
  useLayoutEffect(() => {
    if (!house || !measureRef.current) return;
    const next: Record<string, number> = {};
    measureRef.current.querySelectorAll<HTMLElement>('[data-flow-key]').forEach((el) => {
      next[el.dataset.flowKey as string] = Math.ceil(el.getBoundingClientRect().height);
    });
    setHeights((prev) => (JSON.stringify(prev) === JSON.stringify(next) ? prev : next));
  });
  const PX_PER_MM = 96 / 25.4;
  const textPages: FlowItem[][] = [];
  if (house) {
    let cur: FlowItem[] = [];
    let used = 0;
    let cap = (297 - 48 - 21) * PX_PER_MM; // page 1: under the banner
    const capOther = (297 - 25 - 21) * PX_PER_MM;
    for (const it of flow) {
      const h = heights[it.key] ?? 0;
      // A piece taller than any page stays where it is when the page is
      // still mostly empty (Word would split it; this preview cannot).
      if (cur.length && used + h > cap && (h <= capOther || used > cap / 2)) {
        const carry: FlowItem[] = [];
        while (cur.length > 1 && cur[cur.length - 1].keep) carry.unshift(cur.pop() as FlowItem);
        textPages.push(cur);
        cur = carry;
        used = carry.reduce((a, c) => a + (heights[c.key] ?? 0), 0);
        cap = capOther;
      }
      cur.push(it);
      used += h;
    }
    if (cur.length) textPages.push(cur);
    totalPages = textPages.length;
  }
  const narrativeNode = (b: any, pieces: Piece[] | undefined, live: boolean) => (
    <NarrativeBlock
      block={b}
      onChange={live ? onBlockChange : undefined}
      editable={live && editable}
      clauseContext={clauseContext}
      isFormEditor={false}
      recordersBlock={isCause(b) ? recordersBlock : undefined}
      onRecordersChange={live ? onBlockChange : undefined}
      reportId={report?.id}
      pieces={pieces}
      onEditStart={live ? (field) => setEditing({ id: String(b.id), field }) : undefined}
      editField={!pieces && editing?.id === String(b.id) ? editing.field : undefined}
      onEditEnd={() => setEditing(null)}
    />
  );
  const flowNode = (it: FlowItem, live: boolean): React.ReactNode => {
    if (it.key === '__title') return <p className="mca-title" data-testid={live ? 'report-title' : undefined}>{reportTitle(metadata, repNum)}</p>;
    if (it.key === '__photos_heading') return <p className="mca-heading mca-center">{PHOTOS_HEADING}</p>;
    if (it.key === '__closing') {
      return (
        <>
          {annexureBlocks.map((ab) => <AnnexuresBlock key={ab.id} block={ab} />)}
          {fixedTextBlocks.map((fb) => <FixedTextBlock key={fb.id} block={fb} metadata={metadata} blocks={blocks} />)}
        </>
      );
    }
    if (it.block?.type === 'narrative') return narrativeNode(it.block, undefined, live);
    return it.block ? renderBlock(it.block, live) : null;
  };
  /** A page's items; the pieces of one section (rows of the cover table, rows of photos) next to each other print together. */
  const renderItems = (items: FlowItem[], live: boolean): React.ReactNode[] => {
    const out: React.ReactNode[] = [];
    const sameKind = (a: FlowItem, b: FlowItem) =>
      a.piece ? Boolean(b.piece) : a.photos ? Boolean(b.photos) : a.row !== undefined && b.row !== undefined;
    for (let i = 0; i < items.length; ) {
      const it = items[i];
      let n = 1;
      while (i + n < items.length && items[i + n].block?.id === it.block?.id && sameKind(it, items[i + n])) n += 1;
      const group = items.slice(i, i + n);
      let node: React.ReactNode;
      if (it.piece) node = narrativeNode(it.block, group.map((g) => g.piece as Piece), live);
      else if (it.photos) {
        node = (
          <PhotoPlateBlock
            block={it.block}
            photoSlice={group.flatMap((g) => g.photos as PreviewPhoto[])}
            assets={assets}
            reportId={report?.id}
            showHeading={false}
          />
        );
      } else if (it.row !== undefined) {
        node = (
          <ParticularsBlock
            block={it.block}
            onChange={live ? onBlockChange : undefined}
            editable={live && editable}
            rowRange={[it.row, (group[group.length - 1].row as number) + 1]}
          />
        );
      } else node = flowNode(it, live);
      out.push(
        <div key={it.key} style={{ display: 'flow-root' }}>
          {node}
        </div>
      );
      i += n;
    }
    return out;
  };

  const handlePrint = () => {
    window.print();
  };

  const ready = async () => (beforeDownload ? beforeDownload() : true);

  const handleDownloadDocx = async () => {
    if (report?.id && (await ready())) {
      window.location.href = getDownloadDocxUrl(report.id);
    }
  };

  const handleDownloadPdf = async () => {
    if (report?.id && (await ready())) {
      window.location.href = getDownloadPdfUrl(report.id);
    }
  };

  const handleOpenServerHtml = async () => {
    if (report?.id && (await ready())) {
      window.open(getPreviewHtmlUrl(report.id), '_blank');
    }
  };

  return (
    <div className="report-preview-wrapper flex flex-col space-y-4">
      {/* PREVIEW CONTROLS TOOLBAR */}
      <div className="sticky top-20 z-30 bg-white/95 backdrop-blur-md px-4 py-3 rounded-xl border border-slate-300 shadow-sm flex flex-wrap justify-between items-center gap-3 print:hidden">
        <div className="flex items-center gap-3">
          {onBackToEdit && (
            <button
              type="button"
              onClick={onBackToEdit}
              className="flex items-center gap-1 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg transition"
            >
              <FileText className="w-3.5 h-3.5" />
              Edit Mode
            </button>
          )}

          <div className="h-4 w-px bg-slate-300" />

          {editable && onBlockChange && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 bg-blue-50 border border-blue-200 text-blue-800 text-xs font-semibold rounded-lg shadow-2xs">
              <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse" />
              <span>Direct In-Place Editing Active</span>
            </div>
          )}

          {/* View Mode Toggle */}
          <div className="flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-xs">
            <button
              type="button"
              onClick={() => setViewMode('all')}
              className={`px-2.5 py-1 rounded-md font-medium transition ${
                viewMode === 'all'
                  ? 'bg-white text-blue-900 shadow-2xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              All Pages ({totalPages})
            </button>
            <button
              type="button"
              onClick={() => setViewMode('paginated')}
              className={`px-2.5 py-1 rounded-md font-medium transition ${
                viewMode === 'paginated'
                  ? 'bg-white text-blue-900 shadow-2xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Single Page
            </button>
          </div>

          {viewMode === 'paginated' && (
            <div className="flex items-center gap-1 text-xs">
              <button
                type="button"
                disabled={currentPage <= 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                className="p-1 rounded hover:bg-slate-100 disabled:opacity-30"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="font-semibold text-slate-700 font-mono">
                {currentPage} / {totalPages}
              </span>
              <button
                type="button"
                disabled={currentPage >= totalPages}
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                className="p-1 rounded hover:bg-slate-100 disabled:opacity-30"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

        {/* Right Tools: Zoom, Print, DOCX */}
        <div className="flex items-center gap-2">
          <div className="flex items-center bg-slate-100 rounded-lg p-0.5 border border-slate-200 text-xs">
            <button
              type="button"
              onClick={() => setZoom((z) => Math.max(50, z - 10))}
              className="p-1.5 text-slate-600 hover:text-slate-900 rounded"
              title="Zoom out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="px-2 font-mono font-semibold text-slate-700 min-w-[48px] text-center">
              {zoom}%
            </span>
            <button
              type="button"
              onClick={() => setZoom((z) => Math.min(150, z + 10))}
              className="p-1.5 text-slate-600 hover:text-slate-900 rounded"
              title="Zoom in"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setZoom(100)}
              className="p-1.5 text-slate-600 hover:text-slate-900 rounded"
              title="Reset zoom"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          </div>

          <button
            type="button"
            onClick={handlePrint}
            className="flex items-center gap-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-200 transition"
          >
            <Printer className="w-3.5 h-3.5" />
            Print / PDF
          </button>

          {report?.id && (
            <button
              type="button"
              onClick={handleOpenServerHtml}
              className="flex items-center gap-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-200 transition"
              title="Open pure server-rendered A4 HTML preview in new tab"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              Server HTML
            </button>
          )}

          {report?.id && (
            <button
              type="button"
              onClick={handleDownloadDocx}
              className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-3 py-1.5 rounded-lg shadow-2xs transition"
            >
              <Download className="w-3.5 h-3.5" />
              Download DOCX
            </button>
          )}

          {report?.id && (
            <button
              type="button"
              onClick={handleDownloadPdf}
              className="flex items-center gap-1.5 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold px-3 py-1.5 rounded-lg shadow-2xs transition"
              title="Download PDF via LibreOffice headless (proof view)"
            >
              <Download className="w-3.5 h-3.5" />
              Download PDF
            </button>
          )}
        </div>
      </div>

      {/* CANVAS CONTAINER */}
      <HouseStyleContext.Provider value={house}>
      {house && (
        <div
          ref={measureRef}
          aria-hidden
          className="mca-page"
          style={{ position: 'absolute', left: '-10000px', top: 0, width: '15.71cm', visibility: 'hidden', pointerEvents: 'none' }}
        >
          {flow.map((it) => (
            <div key={it.key} data-flow-key={it.key} style={{ display: 'flow-root' }}>
              {renderItems([it], false)}
            </div>
          ))}
        </div>
      )}
      <div
        className="preview-canvas bg-slate-200/80 p-8 rounded-2xl border border-slate-300 shadow-inner overflow-x-auto min-h-screen flex flex-col items-center print:bg-white print:p-0 print:border-none print:shadow-none"
        style={{
          transform: zoom !== 100 ? `scale(${zoom / 100})` : undefined,
          transformOrigin: 'top center',
        }}
      >
        {house && textPages.map((keys, i) =>
          viewMode === 'all' || currentPage === i + 1 ? (
            <PageContainer
              key={`text-page-${i}`}
              pageNumber={i + 1}
              totalPages={totalPages}
              reportNumber={repNum}
              reportLabel={headerLabel}
              isQc={isQc}
              house
              banner={i === 0}
            >
              {renderItems(keys, true)}
            </PageContainer>
          ) : null
        )}

        {/* PAGE 1: Overview & Tables */}
        {!house && (viewMode === 'all' || currentPage === 1) && (
          <PageContainer
            pageNumber={1}
            totalPages={totalPages}
            reportNumber={repNum}
            reportLabel={headerLabel}
            isQc={isQc}
            house={house}
            banner={house}
          >
            {house ? (
              <p className="mca-title" data-testid="report-title">{reportTitle(metadata, repNum)}</p>
            ) : (
            <div className="text-center my-1.5">
              {editable && onBlockStateChange ? (
                <input
                  type="text"
                  value={blockState?.report_title || 'Marine Cargo Survey & QC Inspection Report'}
                  onChange={(e) => onBlockStateChange({ ...blockState, report_title: e.target.value })}
                  className="w-full text-[15px] font-bold text-[#00387A] text-center uppercase tracking-wide bg-transparent border-none outline-none hover:bg-blue-50/40 focus:bg-white focus:ring-1 focus:ring-blue-500 rounded px-2 py-0.5 transition-colors"
                />
              ) : (
                <h1 className="text-[16px] font-bold text-[#00387A] uppercase tracking-wide">
                  {blockState?.report_title || 'Marine Cargo Survey & QC Inspection Report'}
                </h1>
              )}
            </div>
            )}

            {page1Blocks.map((b) => renderBlock(b))}

            {/* If no photos, render annexures and fixed text at bottom of page 1 */}
            {photoPages.length === 0 && (
              <>
                {annexureBlocks.map((ab) => (
                  <AnnexuresBlock key={ab.id} block={ab} />
                ))}
                {fixedTextBlocks.map((fb) => (
                  <FixedTextBlock key={fb.id} block={fb} metadata={metadata} blocks={blocks} />
                ))}
              </>
            )}
          </PageContainer>
        )}

        {/* PHOTO PAGES (8 or 6 to a page, as set on the photo section); survey reports flow them with the text */}
        {!house && photoPages.map(({ block: pb, slice, first }, pageIdx) => {
          const pageNum = 2 + pageIdx;
          const isLast = pageNum === totalPages;

          if (viewMode === 'paginated' && currentPage !== pageNum) {
            return null;
          }

          return (
            <PageContainer
              key={`photo-page-${pageIdx}`}
              pageNumber={pageNum}
              totalPages={totalPages}
              reportNumber={repNum}
              reportLabel={headerLabel}
              isQc={isQc}
              photoPage
            >
              <PhotoPlateBlock
                block={pb}
                photoSlice={slice}
                assets={assets}
                reportId={report?.id}
                showHeading={first && layoutOf(pb).show_heading}
              />

              {/* Annexures and Fixed text on the final page */}
              {isLast && (
                <>
                  {annexureBlocks.map((ab) => (
                    <AnnexuresBlock key={ab.id} block={ab} />
                  ))}
                  {fixedTextBlocks.map((fb) => (
                    <FixedTextBlock key={fb.id} block={fb} metadata={metadata} blocks={blocks} />
                  ))}
                </>
              )}
            </PageContainer>
          );
        })}
      </div>
      </HouseStyleContext.Provider>
    </div>
  );
};

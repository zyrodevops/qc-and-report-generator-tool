import React, { useState, useMemo } from 'react';
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
} from './blocks';
import { getDownloadDocxUrl, getDownloadPdfUrl, getPreviewHtmlUrl } from '../../api/client';

export interface ReportPreviewProps {
  report?: any;
  blockState: any;
  reportNumber?: string;
  onBackToEdit?: () => void;
  onBlockChange?: (updatedBlock: any) => void;
  onBlockStateChange?: (updatedState: any) => void;
  editable?: boolean;
}

export const ReportPreview: React.FC<ReportPreviewProps> = ({
  report,
  blockState,
  reportNumber,
  onBackToEdit,
  onBlockChange,
  onBlockStateChange,
  editable = true,
}) => {
  const [zoom, setZoom] = useState<number>(100);
  const [viewMode, setViewMode] = useState<'paginated' | 'all'>('all');
  const [currentPage, setCurrentPage] = useState<number>(1);

  // Compute block state with pure zero-drift logic
  const computedState = useMemo(() => {
    return computeBlockState(blockState);
  }, [blockState]);

  const blocks: any[] = computedState?.blocks || [];
  const metadata = computedState?.metadata || report?.block_state?.metadata || {};
  const repNum = reportNumber || report?.report_number || metadata?.number || 'QC-DRAFT';
  const assets = computedState?.assets || {};

  // Separate blocks for realistic pagination:
  // Page 1: Overview & Survey Data
  // Page 2+: Evidence (photos), Documentation (annexures), Legal (fixed_text)
  const page1Blocks = blocks.filter((b) =>
    ['parties', 'attendance', 'particulars', 'timeline', 'narrative', 'measurements', 'table', 'reconciliation', 'inventory', 'unit_group'].includes(b.type)
  );
  const photoBlocks = blocks.filter((b) => b.type === 'photo_plate');
  const fixedTextBlocks = blocks.filter((b) => b.type === 'fixed_text');
  const annexureBlocks = blocks.filter((b) => b.type === 'annexures');

  // Flatten all photos for pagination
  const allPhotos: Array<{
    number: number;
    caption: string;
    assetId?: string;
    imagePath?: string;
  }> = [];

  photoBlocks.forEach((pb) => {
    const computedGroups = pb._computed?.groups || {};
    (pb.groups || []).forEach((g: any) => {
      const gid = g.id || '';
      const obs = g.observation || '';
      const assetIds: string[] = g.asset_ids || [];
      const grpComputed = computedGroups[gid] || {};
      const numbers: number[] =
        grpComputed.numbers || assetIds.map((_, i) => i + 1);

      assetIds.forEach((aid, idx) => {
        const num = numbers[idx] || idx + 1;
        const asset = assets[aid] || {};
        const derived = asset.derived_paths || asset.derived || {};
        const repId = report?.id || blockState?.id;
        const imgPath =
          asset.url ||
          (aid && repId ? `/api/reports/${repId}/assets/${aid}/image` : '') ||
          (typeof derived.display === 'string' && derived.display.startsWith('/api') ? derived.display : '') ||
          (typeof asset.original_path === 'string' && asset.original_path.startsWith('/api') ? asset.original_path : '');

        allPhotos.push({
          number: num,
          caption: `Photo No. ${num} \u2014 ${obs}`,
          assetId: aid,
          imagePath: imgPath,
        });
      });
    });
  });

  // Chunk photos 4 per page
  const photoPages: Array<typeof allPhotos> = [];
  if (allPhotos.length > 0) {
    for (let i = 0; i < allPhotos.length; i += 4) {
      photoPages.push(allPhotos.slice(i, i + 4));
    }
  }

  // Calculate total pages
  let totalPages = 1; // Page 1
  if (photoPages.length > 0) {
    totalPages += photoPages.length;
  } else if (fixedTextBlocks.length > 0 && page1Blocks.length > 3) {
    totalPages += 1;
  }

  const handlePrint = () => {
    window.print();
  };

  const handleDownloadDocx = () => {
    if (report?.id) {
      window.location.href = getDownloadDocxUrl(report.id);
    }
  };

  const handleDownloadPdf = () => {
    if (report?.id) {
      window.location.href = getDownloadPdfUrl(report.id);
    }
  };

  const handleOpenServerHtml = () => {
    if (report?.id) {
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
      <div
        className="preview-canvas bg-slate-200/80 p-8 rounded-2xl border border-slate-300 shadow-inner overflow-x-auto min-h-screen flex flex-col items-center print:bg-white print:p-0 print:border-none print:shadow-none"
        style={{
          transform: zoom !== 100 ? `scale(${zoom / 100})` : undefined,
          transformOrigin: 'top center',
        }}
      >
        {/* PAGE 1: Overview & Tables */}
        {(viewMode === 'all' || currentPage === 1) && (
          <PageContainer
            pageNumber={1}
            totalPages={totalPages}
            reportNumber={repNum}
          >
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

            {page1Blocks.map((b) => {
              if (b.type === 'parties') {
                return (
                  <PartiesBlock
                    key={b.id}
                    block={b}
                    onChange={onBlockChange}
                    editable={editable}
                  />
                );
              }
              if (b.type === 'attendance') {
                return (
                  <AttendanceBlock
                    key={b.id}
                    block={b}
                    onChange={onBlockChange}
                    editable={editable}
                  />
                );
              }
              if (b.type === 'particulars') {
                return (
                  <ParticularsBlock
                    key={b.id}
                    block={b}
                    onChange={onBlockChange}
                    editable={editable}
                  />
                );
              }
              if (b.type === 'timeline') {
                return (
                  <TimelineBlock
                    key={b.id}
                    block={b}
                    onChange={onBlockChange}
                    editable={editable}
                  />
                );
              }
              if (b.type === 'narrative') {
                return (
                  <NarrativeBlock
                    key={b.id}
                    block={b}
                    onChange={onBlockChange}
                    editable={editable}
                    commodity={
                      metadata?.commodity ||
                      (blockState?.report_title?.match(/APPLE|MANDARIN|ORANGE|GRAPE|KIWI|PEAR|BLUEBERRY|CHERRY|PLUM|DRAGON|AVOCADO/i)?.[0]?.toUpperCase()) ||
                      'APPLE'
                    }
                  />

                );
              }
              if (b.type === 'measurements') {
                return (
                  <MeasurementsBlock
                    key={b.id}
                    block={b}
                    onChange={onBlockChange}
                    editable={editable}
                  />
                );
              }
              if (b.type === 'table') {
                return (
                  <TableBlock
                    key={b.id}
                    block={b}
                    computed={b._computed}
                    onChange={onBlockChange}
                    editable={editable}
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
              return null;
            })}

            {/* If no photos, render annexures and fixed text at bottom of page 1 */}
            {photoPages.length === 0 && (
              <>
                {annexureBlocks.map((ab) => (
                  <AnnexuresBlock key={ab.id} block={ab} />
                ))}
                {fixedTextBlocks.map((fb) => (
                  <FixedTextBlock key={fb.id} block={fb} metadata={metadata} />
                ))}
              </>
            )}
          </PageContainer>
        )}

        {/* PHOTO PAGES (Chunked 4 per page) */}
        {photoPages.map((slice, pageIdx) => {
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
            >
              <PhotoPlateBlock
                block={photoBlocks[0] || { label: 'Survey Photographs' }}
                photoSlice={slice}
                assets={assets}
                reportId={report?.id}
              />

              {/* Annexures and Fixed text on the final page */}
              {isLast && (
                <>
                  {annexureBlocks.map((ab) => (
                    <AnnexuresBlock key={ab.id} block={ab} />
                  ))}
                  {fixedTextBlocks.map((fb) => (
                    <FixedTextBlock key={fb.id} block={fb} metadata={metadata} />
                  ))}
                </>
              )}
            </PageContainer>
          );
        })}
      </div>
    </div>
  );
};

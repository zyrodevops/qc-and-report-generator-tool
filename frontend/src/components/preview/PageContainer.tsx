import React from 'react';

export interface PageContainerProps {
  pageNumber: number;
  totalPages: number;
  headerLeft?: string;
  headerRight?: string;
  reportNumber?: string;
  children: React.ReactNode;
  className?: string;
  /** Photo pages: the Word file's photo margins, so 8 photos fit as they do there. */
  photoPage?: boolean;
}

export const PageContainer: React.FC<PageContainerProps> = ({
  pageNumber,
  totalPages,
  headerLeft = 'MARINE CARGO AGENCIES',
  headerRight,
  reportNumber,
  children,
  className = '',
  photoPage = false,
}) => {
  const formattedHeaderRight =
    headerRight ||
    (reportNumber
      ? `IN-HOUSE QC INSPECTION REPORT # ${reportNumber}`
      : 'IN-HOUSE QC INSPECTION REPORT');

  return (
    <div
      className={`page-container a4-page w-[210mm] min-h-[297mm] max-w-[210mm] mx-auto my-6 bg-white shadow-xl ring-1 ring-slate-900/10 box-border flex flex-col justify-between relative transition-all print:w-full print:min-h-0 print:shadow-none print:ring-0 print:m-0 print:page-break-after-always ${className}`}
      style={{
        width: '210mm',
        minHeight: '297mm',
        // The photo table is 16.5 cm wide, a little wider than the text area,
        // as in the client's reports; the running header and footer sit in
        // the margins so four rows of photos fit.
        ...(photoPage
          ? { paddingTop: '0.35in', paddingBottom: '0.35in', paddingLeft: '2.0cm', paddingRight: '2.0cm' }
          : { paddingTop: '0.446in', paddingBottom: '1.0in', paddingLeft: '1.083in', paddingRight: '1.0in' }),
      }}
    >
      {/* Running Header */}
      <header className="flex justify-between items-end pb-1.5 mb-4 border-b-2 border-[#00387A] text-slate-800">
        <div className="font-bold text-xs uppercase tracking-wider text-slate-800 font-sans">
          {headerLeft}
        </div>
        <div className="font-mono font-bold text-xs text-[#00387A] tracking-tight">
          {formattedHeaderRight}
        </div>
      </header>

      {/* Page Content Body */}
      <main className="flex-1 flex flex-col space-y-4 text-slate-900">
        {children}
      </main>

      {/* Running Footer (Page X of Y) */}
      <footer className="pt-2 mt-4 border-t border-slate-200 flex justify-between items-center text-[10px] text-slate-500 font-sans">
        <span>Marine Cargo Agencies &bull; Issued Without Prejudice</span>
        <span className="font-bold text-slate-700 tracking-wider">
          Page {pageNumber} of {totalPages}
        </span>
        <span className="italic">Confidential QC Inspection</span>
      </footer>
    </div>
  );
};

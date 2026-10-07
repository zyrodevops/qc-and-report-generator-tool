import React from 'react';
import { COMPANY, bannerUrl } from '../../utils/houseStyle';

export interface PageContainerProps {
  pageNumber: number;
  totalPages: number;
  headerLeft?: string;
  headerRight?: string;
  reportNumber?: string;
  /** e.g. "FINAL SURVEY REPORT"; the running header reads "<label> NO. <number>". */
  reportLabel?: string;
  /** QC reports keep their own header and footer wording. */
  isQc?: boolean;
  /**
   * Survey reports: the client's page — a thin black border 24 pt in from the
   * edge, the banner across the top of page 1, the company name and report
   * number in small dark-blue capitals from page 2, "Page X of Y" bottom right.
   */
  house?: boolean;
  /** Page 1 of a survey report shows the banner (when the server has one). */
  banner?: boolean;
  children: React.ReactNode;
  className?: string;
  /** Photo pages: the Word file's photo margins, so 8 photos fit as they do there. */
  photoPage?: boolean;
}

const RUNNING: React.CSSProperties = {
  fontFamily: "'Arial Narrow', Arial, sans-serif",
  fontWeight: 700,
  fontSize: '9pt',
  color: '#002060',
};

export const PageContainer: React.FC<PageContainerProps> = ({
  pageNumber,
  totalPages,
  headerLeft = 'MARINE CARGO AGENCIES',
  headerRight,
  reportNumber,
  reportLabel,
  isQc = false,
  house = false,
  banner = false,
  children,
  className = '',
  photoPage = false,
}) => {
  const [bannerFailed, setBannerFailed] = React.useState(false);
  const label = isQc ? 'IN-HOUSE QC INSPECTION REPORT' : reportLabel || 'SURVEY REPORT';
  const formattedHeaderRight =
    headerRight || (reportNumber ? `${label} ${isQc ? '#' : 'NO.'} ${reportNumber}` : label);

  if (house) {
    const showBanner = banner && !bannerFailed;
    return (
      <div
        className={`page-container a4-page mca-page w-[210mm] min-h-[297mm] max-w-[210mm] mx-auto my-6 bg-white shadow-xl ring-1 ring-slate-900/10 box-border flex flex-col relative print:shadow-none print:ring-0 print:m-0 ${className}`}
        style={{ width: '210mm', minHeight: '297mm', padding: '2.5cm 2.54cm 2.1cm 2.75cm' }}
        data-testid="a4-page"
      >
        {/* Page border, 24 pt in from the page edge */}
        <div className="absolute pointer-events-none" style={{ inset: '24pt', border: '0.5pt solid #000' }} />

        {showBanner ? (
          <img
            src={bannerUrl()}
            alt="Letterhead"
            onError={() => setBannerFailed(true)}
            className="absolute"
            style={{ top: '24pt', left: '24pt', width: 'calc(210mm - 48pt)', height: 'auto' }}
            data-testid="a4-banner"
          />
        ) : (
          !banner && (
            <header
              className="absolute flex justify-between"
              style={{ top: '1.3cm', left: '2.75cm', right: '2.54cm', ...RUNNING }}
              data-testid="a4-running-header"
            >
              <span>{COMPANY}</span>
              <span>{formattedHeaderRight.toUpperCase()}</span>
            </header>
          )
        )}

        {/* Page 1: the body starts under the banner (19.3 cm x 3.7 cm) */}
        <main className="flex-1 flex flex-col text-black" style={showBanner ? { marginTop: '2.3cm' } : undefined}>
          {children}
        </main>

        <footer className="absolute" style={{ bottom: '1.1cm', right: '2.54cm', ...RUNNING }} data-testid="a4-footer">
          Page {pageNumber} of {totalPages}
        </footer>
      </div>
    );
  }

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
        <span className="italic">{isQc ? 'Confidential QC Inspection' : 'Confidential'}</span>
      </footer>
    </div>
  );
};

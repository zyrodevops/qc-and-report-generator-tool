import React, { useState, useEffect } from 'react';
import { ReportList } from './pages/ReportList';
import { ReportForm } from './pages/ReportForm';
import { LoginPage } from './pages/LoginPage';
import { PhotosPage } from './pages/PhotosPage';
import { ReportSummary, UserSession, getStoredUser, fetchCurrentUser, logout } from './api/client';
import { Anchor, LogOut, Loader2, Camera } from 'lucide-react';

// ── App ──────────────────────────────────────────────────────────────────────
type AppView = 'reports' | 'photos';

export function App() {
  const [currentUser, setCurrentUser] = useState<UserSession | null>(getStoredUser());
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [selectedReport, setSelectedReport] = useState<ReportSummary | null>(null);
  const [view, setView] = useState<AppView>('reports');

  useEffect(() => {
    fetchCurrentUser()
      .then((user) => { setCurrentUser(user); })
      .finally(() => { setCheckingAuth(false); });
  }, []);

  const handleLogout = async () => {
    await logout();
    setCurrentUser(null);
    setSelectedReport(null);
    setView('reports');
  };

  const handleOpenPhotoStudio = () => {
    setView('photos');
    // Keep selectedReport in memory so Photos page knows which report to link
  };

  if (checkingAuth) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center text-white gap-3">
        <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
        <span className="text-sm font-medium">Initializing surveyor session...</span>
      </div>
    );
  }

  if (!currentUser) {
    return <LoginPage onLoginSuccess={(user) => setCurrentUser(user)} />;
  }

  // ── Photo Studio Page (full-screen, replaces main content) ────────────────
  if (view === 'photos') {
    return (
      <PhotosPage
        reportId={selectedReport?.id}
        reportNumber={selectedReport?.report_number}
        onClose={() => setView('reports')}
      />
    );
  }

  // ── Main App Shell ─────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* GLOBAL HEADER */}
      <header className="bg-slate-900 text-white border-b border-slate-800 shadow-md">
        <div className="max-w-7xl mx-auto px-4 py-3.5 flex justify-between items-center">
          {/* Logo / Home */}
          <div
            onClick={() => { setSelectedReport(null); setView('reports'); }}
            className="flex items-center gap-2.5 cursor-pointer select-none group"
          >
            <div className="bg-blue-600 p-2 rounded-lg group-hover:bg-blue-500 transition">
              <Anchor className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="font-black tracking-tight text-lg leading-tight block">
                MARINE CARGO AGENCIES
              </span>
              <span className="text-xs text-blue-400 font-medium block">
                Survey & QC Report Platform • IRDAI Licensed
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Photo Studio — prominently styled */}
            <button
              type="button"
              onClick={handleOpenPhotoStudio}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 border border-indigo-500 text-white text-sm px-4 py-2 rounded-xl transition font-semibold shadow-md cursor-pointer"
              title="Open Photo Annexure Studio — Normal, Bulk & Pro modes"
            >
              <Camera className="w-4 h-4" />
              <span>📷 Photo Studio</span>
              {selectedReport && (
                <span className="text-[10px] bg-indigo-400/40 border border-indigo-300/30 px-2 py-0.5 rounded-full font-medium">
                  {selectedReport.report_number}
                </span>
              )}
            </button>

            <div className="flex items-center gap-2 bg-slate-800 border border-slate-700 px-3 py-1.5 rounded-lg text-xs">
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              <span className="font-semibold text-white">Client Access Active</span>
            </div>

            <button
              type="button"
              onClick={handleLogout}
              className="flex items-center gap-1 bg-slate-800 hover:bg-red-900/60 hover:border-red-700 border border-slate-700 text-slate-300 hover:text-red-200 text-xs px-2.5 py-1.5 rounded-lg transition cursor-pointer"
              title="Logout"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Logout</span>
            </button>
          </div>
        </div>
      </header>

      {/* MAIN CONTAINER */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-8">
        {selectedReport ? (
          <ReportForm report={selectedReport} onBack={() => setSelectedReport(null)} />
        ) : (
          <ReportList onSelectReport={(rep) => setSelectedReport(rep)} />
        )}
      </main>

      {/* GLOBAL FOOTER */}
      <footer className="bg-white border-t border-gray-200 py-4 text-center text-xs text-gray-500">
        © 2026 Marine Cargo Agencies Private Limited. All calculations computed fresh at render time per Master Spec v3.1.
      </footer>
    </div>
  );
}

export default App;

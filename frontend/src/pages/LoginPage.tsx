import React, { useState } from 'react';
import { Anchor, Lock, Mail, ArrowRight, ShieldCheck, Loader2 } from 'lucide-react';
import { login, UserSession } from '../api/client';

interface LoginPageProps {
  onLoginSuccess: (user: UserSession) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const [email, setEmail] = useState('surveyor@example.com');
  const [password, setPassword] = useState('Password123!');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const user = await login(email, password);
      onLoginSuccess(user);
    } catch (err: any) {
      setError(err.message || 'Invalid email or password');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setError(null);
    setLoading(true);
    login(demoEmail, demoPass)
      .then((user) => onLoginSuccess(user))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col justify-center items-center p-4">
      {/* BRANDING LOGO */}
      <div className="max-w-md w-full text-center space-y-3 mb-8">
        <div className="inline-flex items-center justify-center p-3 bg-blue-600 rounded-2xl shadow-lg shadow-blue-500/20 mb-2">
          <Anchor className="w-8 h-8 text-white" />
        </div>
        <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
          MARINE CARGO AGENCIES
        </h1>
        <p className="text-sm text-slate-400">
          Survey & QC Report Generation Platform • IRDAI Licensed
        </p>
      </div>

      {/* LOGIN CARD */}
      <div className="max-w-md w-full bg-white rounded-2xl shadow-2xl p-8 space-y-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Surveyor Login</h2>
          <p className="text-xs text-gray-500 mt-1">
            Authenticate to allocate report numbers, edit surveys, and generate DOCX reports.
          </p>
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-xs font-semibold flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-red-500"></span>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1.5">
              Surveyor Email
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="surveyor@example.com"
                className="w-full pl-9 pr-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none text-gray-900 font-medium"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1.5">
              Password
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-9 pr-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none text-gray-900 font-medium"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm rounded-lg shadow-md hover:shadow-lg transition flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                Sign In to Platform <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        {/* QUICK ONE-CLICK LOGIN FOR LOCAL TESTING */}
        <div className="pt-4 border-t border-gray-100 space-y-2">
          <span className="block text-xs font-semibold text-gray-500 uppercase tracking-wider text-center">
            One-Click Local Test Accounts
          </span>
          <div className="grid grid-cols-1 gap-2">
            <button
              type="button"
              onClick={() => handleQuickLogin('surveyor@example.com', 'Password123!')}
              className="w-full text-left px-3 py-2 bg-gray-50 hover:bg-blue-50 hover:border-blue-300 border border-gray-200 rounded-lg text-xs font-medium text-gray-700 flex items-center justify-between transition"
            >
              <span>
                <strong className="text-gray-900 block font-semibold">Kishan Singh (Surveyor)</strong>
                <span className="text-gray-500 text-[11px]">surveyor@example.com</span>
              </span>
              <ShieldCheck className="w-4 h-4 text-blue-600" />
            </button>

            <button
              type="button"
              onClick={() => handleQuickLogin('surveyor@oceanic-claims.test', 'SafePassword123!')}
              className="w-full text-left px-3 py-2 bg-gray-50 hover:bg-blue-50 hover:border-blue-300 border border-gray-200 rounded-lg text-xs font-medium text-gray-700 flex items-center justify-between transition"
            >
              <span>
                <strong className="text-gray-900 block font-semibold">Oceanic Surveyor</strong>
                <span className="text-gray-500 text-[11px]">surveyor@oceanic-claims.test</span>
              </span>
              <ShieldCheck className="w-4 h-4 text-blue-600" />
            </button>
          </div>
        </div>
      </div>

      <p className="mt-8 text-xs text-slate-500 text-center">
        © 2026 Marine Cargo Agencies Pvt. Ltd. All rights reserved.
      </p>
    </div>
  );
};


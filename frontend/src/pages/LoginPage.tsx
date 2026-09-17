import React, { useState } from 'react';
import { Anchor, Lock, ArrowRight, Eye, EyeOff, Loader2, KeyRound } from 'lucide-react';
import { login, UserSession } from '../api/client';

interface LoginPageProps {
  onLoginSuccess: (user: UserSession) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const [password, setPassword] = useState(import.meta.env.DEV ? 'surveyor123' : '');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const user = await login(password);
      onLoginSuccess(user);
    } catch (err: any) {
      setError(err.message || 'Invalid access password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col justify-center items-center p-4">
      {/* BRANDING LOGO */}
      <div className="max-w-md w-full text-center space-y-3 mb-8">
        <div className="inline-flex items-center justify-center p-3.5 bg-blue-600 rounded-2xl shadow-lg shadow-blue-500/25 mb-2">
          <Anchor className="w-8 h-8 text-white" />
        </div>
        <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
          MARINE CARGO AGENCIES
        </h1>
        <p className="text-sm text-slate-400">
          Cargo Survey & QC Report Platform • IRDAI Licensed
        </p>
      </div>

      {/* LOGIN CARD */}
      <div className="max-w-md w-full bg-white rounded-2xl shadow-2xl p-8 space-y-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <KeyRound className="w-5 h-5 text-blue-600" />
            <h2 className="text-xl font-bold text-gray-900">Protected Client Access</h2>
          </div>
          <p className="text-xs text-gray-500">
            Enter your shared access password to unlock the survey and report generator workspace.
          </p>
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-xs font-semibold flex items-center gap-2 animate-fade-in">
            <span className="w-2 h-2 rounded-full bg-red-500 shrink-0"></span>
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1.5">
              Access Password
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type={showPassword ? 'text' : 'password'}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password..."
                className="w-full pl-9 pr-10 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none text-gray-900 font-medium transition"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || !password.trim()}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm rounded-lg shadow-md hover:shadow-lg transition flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                Unlock Workspace <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        {/* Never print the access key in a production build. */}
        {import.meta.env.DEV && (
          <div className="pt-4 border-t border-gray-100 flex items-center justify-between text-xs text-slate-500">
            <span>Dev access key:</span>
            <code className="px-2 py-0.5 bg-slate-100 font-mono text-slate-800 rounded font-semibold select-all">
              surveyor123
            </code>
          </div>
        )}
      </div>

      <p className="mt-8 text-xs text-slate-500 text-center">
        © 2026 Marine Cargo Agencies Pvt. Ltd. All rights reserved.
      </p>
    </div>
  );
};


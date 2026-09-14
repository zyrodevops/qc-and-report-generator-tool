// Frontend API Client with Authentication and Session Management

export interface UserSession {
  token: string;
  user_id: string;
  email: string;
  full_name: string;
  role: string;
  created_at: string;
}

export interface ReportSummary {
  id: string;
  report_number: string;
  family: string;
  state: string;
  status: string;
  template_id: string;
  version?: number;
  block_state: any;
  created_at: string;
  updated_at: string;
}

export interface CommodityArchetype {
  key: string;
  display: string;
  emoji: string;
  color: string;
  report_count: number;
  unit: 'pcs' | 'kg';
  defect_columns: string[];
  heading_sequence: string[];
  top_narrative_clauses: string[];
}

export interface CreateReportParams {
  template_id: string;
  family?: string;
  year?: number;
  mode?: 'SEA' | 'AIR';
  commodity?: string;
  block_state?: any;
}

const TOKEN_KEY = 'mca_session_token';
const USER_KEY = 'mca_session_user';

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): UserSession | null {
  const data = localStorage.getItem(USER_KEY);
  if (!data) return null;
  try {
    return JSON.parse(data);
  } catch {
    return null;
  }
}

export function setStoredSession(token: string, user: UserSession): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearStoredSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getAuthHeaders(): Record<string, string> {
  const token = getStoredToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ---------------------------------------------------------------------------
// Auth API
// ---------------------------------------------------------------------------

export async function login(arg1: string, arg2?: string): Promise<UserSession> {
  let password = arg1;
  let email: string | undefined = undefined;

  if (arg2 !== undefined) {
    if (arg1.includes('@')) {
      email = arg1;
      password = arg2;
    } else {
      password = arg1;
      email = arg2;
    }
  }

  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(email ? { email, password } : { password }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Access denied' }));
    throw new Error(errorData.detail || 'Invalid access password');
  }

  const data = await res.json();
  const token = data.token;
  const user = data.user;
  setStoredSession(token, user);
  return user;
}

export async function logout(): Promise<void> {
  try {
    await fetch('/api/auth/logout', {
      method: 'POST',
      headers: getAuthHeaders(),
    });
  } catch (err) {
    console.error('Logout error:', err);
  } finally {
    clearStoredSession();
  }
}

export async function fetchCurrentUser(): Promise<UserSession | null> {
  const token = getStoredToken();
  if (!token) return null;

  try {
    const res = await fetch('/api/auth/me', {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      clearStoredSession();
      return null;
    }
    const user = await res.json();
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    return user;
  } catch {
    clearStoredSession();
    return null;
  }
}

// ---------------------------------------------------------------------------
// Reports API
// ---------------------------------------------------------------------------

export async function fetchReports(): Promise<ReportSummary[]> {
  const res = await fetch('/api/reports', {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    if (res.status === 401) {
      clearStoredSession();
      throw new Error('UNAUTHORIZED');
    }
    throw new Error(`Failed to fetch reports: ${res.statusText}`);
  }
  return res.json();
}

export async function createReport(params: CreateReportParams): Promise<ReportSummary> {
  const res = await fetch('/api/reports', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify({
      template_id: params.template_id,
      family: params.family || (params.template_id.includes('qc') ? 'QC_REPORT' : 'SURVEY_REPORT'),
      year: params.year || 2026,
      commodity: params.commodity || 'mandarin',
      block_state: params.block_state || {},
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Failed to create report: ${err}`);
  }
  return res.json();
}

export class VersionConflictError extends Error {
  currentVersion: number;
  submittedVersion: number;

  constructor(currentVersion: number, submittedVersion: number) {
    super(
      `Version conflict: you submitted version ${submittedVersion} but the current version is ${currentVersion}. ` +
      `Re-fetch the report and reapply your changes.`
    );
    this.name = 'VersionConflictError';
    this.currentVersion = currentVersion;
    this.submittedVersion = submittedVersion;
  }
}

/**
 * Patch a report's block_state with optimistic concurrency.
 * Throws VersionConflictError if the server returns 409 (stale version).
 * Returns { new_version } on success.
 */
export async function patchBlockState(
  reportId: string,
  blockState: any,
  version: number
): Promise<{ new_version: number }> {
  const res = await fetch(`/api/reports/${reportId}/block-state`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ block_state: blockState, version }),
  });

  if (res.status === 409) {
    const body = await res.json();
    const detail = body.detail || {};
    throw new VersionConflictError(
      detail.current_version ?? 1,
      detail.submitted_version ?? version
    );
  }

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Failed to update report state (${res.status}): ${err}`);
  }

  return res.json();
}

/** @deprecated Use patchBlockState (with version) instead. */
export async function updateBlockState(reportId: string, blockState: any): Promise<void> {
  const res = await fetch(`/api/reports/${reportId}/block-state`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ block_state: blockState, version: 1 }),
  });
  if (!res.ok) {
    throw new Error(`Failed to update report state: ${res.statusText}`);
  }
}

export function getDownloadDocxUrl(reportId: string): string {
  const token = getStoredToken();
  return `/api/reports/${reportId}/download/docx${token ? `?auth_token=${encodeURIComponent(token)}` : ''}`;
}

export function getDownloadPdfUrl(reportId: string): string {
  const token = getStoredToken();
  return `/api/reports/${reportId}/download/pdf${token ? `?auth_token=${encodeURIComponent(token)}` : ''}`;
}

export async function fetchReport(reportId: string): Promise<ReportSummary> {
  const res = await fetch(`/api/reports/${reportId}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    if (res.status === 401) {
      clearStoredSession();
      throw new Error('UNAUTHORIZED');
    }
    throw new Error(`Failed to fetch report: ${res.statusText}`);
  }
  return res.json();
}

export function getPreviewHtmlUrl(reportId: string): string {
  const token = getStoredToken();
  return `/api/reports/${reportId}/preview/html${token ? `?auth_token=${encodeURIComponent(token)}` : ''}`;
}

export async function fetchCommodities(): Promise<CommodityArchetype[]> {
  const res = await fetch('/api/commodities', {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch commodities: ${res.statusText}`);
  }
  const data = await res.json();
  return data.commodities as CommodityArchetype[];
}

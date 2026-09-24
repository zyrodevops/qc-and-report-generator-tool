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
  category?: 'FRUITS' | 'GENERAL_CARGO';
  description?: string;
  report_count: number;
  unit: 'pcs' | 'kg';
  defect_columns: string[];
  heading_sequence: string[];
  top_narrative_clauses?: string[];

  /**
   * Feature flags derived from the corpus analysis of 451 of the client's own
   * reports. Fruit is the master switch: it decides which sections render,
   * whether a chart is produced and which measurements are offered.
   * See IMPLEMENTATION-SPEC-perishable-fruits.md section 2.
   *
   * Transport mode is deliberately absent — it belongs to the shipment, and is
   * taken from the uploaded transport document or chosen explicitly. It is never
   * inferred from the commodity.
   */
  show_condition_found?: boolean;  // CONDITION FOUND section: 100% Blueberry, 0% Grapes
  show_chart?: boolean;            // defect chart: 97% Blueberry, 9% Apple
  show_penetrometer?: boolean;     // firm fruits only: Pear/Kiwi 100%, berries 0%
  show_brix?: boolean;             // universal except Avocado
  air_observed_pct?: number;       // observed frequency only, not a rule
}

export interface CreateReportParams {
  template_id: string;
  family?: string;
  year?: number;
  mode?: 'SEA' | 'AIR';
  commodity?: string;
  state?: 'PRELIMINARY' | 'FINAL';
  selected_sections?: string[];
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
      // Sent as chosen. A missing fruit is refused by the server, not replaced
      // here with one nobody picked.
      commodity: params.commodity || null,
      state: params.state || 'FINAL',
      selected_sections: params.selected_sections,
      block_state: params.block_state || {},
    }),
  });

  if (!res.ok) {
    const text = await res.text();
    let msg = text;
    try {
      const d = JSON.parse(text).detail;
      msg = typeof d === 'string' ? d : d?.message || text;
    } catch {
      /* not JSON: show as sent */
    }
    throw new Error(`Could not create the report. ${msg}`);
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

export interface ReportTemplate {
  id: string;
  name: string;
  family: 'QC_REPORT' | 'SURVEY_REPORT';
  mode: 'SEA' | 'AIR';
  requires_commodity: boolean;
  block_count: number;
}

/**
 * Report types, read from the database rather than a hardcoded list.
 * The old hardcoded list drifted from the seeded templates and pointed at ids
 * that no longer exist, which would have failed on the template foreign key.
 */
export async function fetchTemplates(): Promise<ReportTemplate[]> {
  const res = await fetch('/api/templates', { headers: getAuthHeaders() });
  if (!res.ok) {
    throw new Error(`Failed to fetch report types: ${res.statusText}`);
  }
  const data = await res.json();
  return data.templates as ReportTemplate[];
}

export async function fetchCommodities(category?: string): Promise<CommodityArchetype[]> {
  const url = category ? `/api/commodities?category=${encodeURIComponent(category)}` : '/api/commodities';
  const res = await fetch(url, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch commodities: ${res.statusText}`);
  }
  const data = await res.json();
  return data.commodities as CommodityArchetype[];
}

// ---------------------------------------------------------------------------
// Tally sheet — Verification Workbench
// ---------------------------------------------------------------------------

export interface TallyCategory {
  key: string;
  label: string;
  role?: 'sound' | 'defect' | 'extra';
}

export interface TallyCellDetail {
  raw_text?: string;
  normalized_value?: number | null;
  confidence?: number;
  cell_image?: string;
  /** Cell box as fractions of the image, so the photo can be highlighted at any display size. */
  bbox_norm?: [number, number, number, number];
  review_status?: 'AUTO_ACCEPTED' | 'NEEDS_REVIEW' | 'AMBIGUOUS';
  source?: 'local' | 'cloud_assist' | 'local+assist';
  assist_value?: number | null;
  agreement?: 'AGREED' | 'DISAGREED' | 'ASSIST_ONLY';
  validation?: { status: string; message?: string };
}

export interface TallyRowCheck {
  /** OK = cells match the written total. MISMATCH = they do not. UNCHECKED = no total was written. */
  status: 'OK' | 'MISMATCH' | 'UNCHECKED';
  delta: number | null;
  message?: string;
}

export interface TallyRow {
  group: string;
  boxes_opened?: number;
  values: Record<string, number>;
  /** What the surveyor wrote in the total column. Null when he wrote none. */
  stated_total: number | null;
  computed_total?: number;
  check?: TallyRowCheck;
  cell_details?: Record<string, TallyCellDetail>;
  provenance?: string;
  /**
   * True for the group subtotal line — the highlighted row whose COUNT cell
   * holds the total pieces examined. That figure is what the row check is
   * proved against; individual carton lines carry no written total.
   */
  is_subtotal?: boolean;
}

export interface TallyExtraction {
  extraction_status: 'OK' | 'PARTIAL' | 'NO_GRID' | 'NO_ENGINE';
  engines_available: string[];
  ocr_engine: string | null;
  quality: { score: number; is_acceptable: boolean; warnings: string[] };
  headers: Record<string, any>;
  table: {
    commodity: string | null;
    unit: string;
    grouping_label: string;
    categories: TallyCategory[];
    rows: TallyRow[];
    column_totals: Record<string, number>;
    /** The sheet's own foot "Total" line, kept aside so it is not counted as a box. */
    sheet_totals?: { values: Record<string, number | null>; stated_total: number | null } | null;
  };
  image: { preview: string; width: number; height: number };
  filename: string;
  /** Present for a spreadsheet import: how its columns were understood. */
  spreadsheet?: {
    sheet_names: string[];
    active_sheet: string | null;
    all_headers: string[];
    column_map: Record<string, string>;
    label_column: string | null;
    total_column: string | null;
    /** Columns that matched nothing — shown so counts are never dropped silently. */
    unmapped_columns: string[];
    row_count: number;
  };
  /** Which reader produced this, and why, so the surveyor knows what he is checking. */
  reader?: {
    used: 'cloud' | 'local' | 'spreadsheet';
    model?: string;
    header_sent?: boolean;
    cloud_configured?: boolean;
    cloud_error?: string | null;
    extra_columns?: string[];
  };
}

/**
 * Load a CSV or Excel tally into the same grid as a photographed sheet.
 * Columns it cannot match come back in spreadsheet.unmapped_columns for the
 * surveyor to map; call again with columnMap once he has.
 */
export async function uploadTallySpreadsheet(
  reportId: string,
  file: File,
  opts: { commodity?: string; sheetName?: string; columnMap?: Record<string, string> } = {},
): Promise<TallyExtraction> {
  const form = new FormData();
  form.append('file', file);
  if (opts.commodity) form.append('commodity', opts.commodity);
  if (opts.sheetName) form.append('sheet_name', opts.sheetName);
  if (opts.columnMap) form.append('column_map_json', JSON.stringify(opts.columnMap));

  const res = await fetch(`/api/reports/${reportId}/import/tally-spreadsheet`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: form,
  });
  if (!res.ok) {
    throw new Error(`Could not read that spreadsheet (${res.status}): ${await res.text()}`);
  }
  return res.json();
}

export interface TallyCapabilities {
  commodity: string | null;
  unit: string;
  categories: TallyCategory[];
  ocr_engines: string[];
  ocr_available: boolean;
  /** True when a key is configured, which makes the hosted model the main reader. */
  cloud_reader: boolean;
  cloud_sends_header: boolean;
  reader: 'cloud' | 'local' | 'none';
}

export async function fetchTallyCapabilities(
  reportId: string,
  commodity?: string,
): Promise<TallyCapabilities> {
  const qs = commodity ? `?commodity=${encodeURIComponent(commodity)}` : '';
  const res = await fetch(`/api/reports/${reportId}/import/tally/capabilities${qs}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`Could not check tally support: ${res.statusText}`);
  return res.json();
}

export async function uploadTallySheet(
  reportId: string,
  file: File,
  opts: { commodity?: string } = {},
): Promise<TallyExtraction> {
  const form = new FormData();
  form.append('file', file);
  if (opts.commodity) form.append('commodity', opts.commodity);

  const res = await fetch(`/api/reports/${reportId}/import/tally-ocr`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: form,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Could not read the tally sheet (${res.status}): ${detail}`);
  }
  return res.json();
}

/**
 * Write the checked grid into the report.
 * The server recomputes every row total and refuses rows that do not tie out,
 * so a 422 here means the sheet still disagrees with itself.
 */
export async function applyTallyGrid(
  reportId: string,
  payload: { headers: Record<string, any>; table: any; block_id?: string },
): Promise<{ block_state: any; version: number }> {
  const res = await fetch(`/api/reports/${reportId}/import/tally-ocr/apply`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify(payload),
  });

  if (res.status === 422) {
    const body = await res.json().catch(() => null);
    const d = body?.detail;
    const rows = Array.isArray(d?.rows) ? ` (${d.rows.join(', ')})` : '';
    throw new Error(`${d?.message || 'Some rows do not add up.'}${rows}`);
  }
  if (!res.ok) {
    throw new Error(`Could not save the tally (${res.status}): ${await res.text()}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Standard wording — the client's own, with other reports' facts blanked
// ---------------------------------------------------------------------------

/** One idea a section carries; adding it inserts that idea's sentences. */
export interface WordingTopic {
  topic: string;
  label: string;
  description: string;
  /** A list item (a document name): shown as a small chip. */
  compact: boolean;
  /** The client's sentences, in his layout. Words in [BRACKETS] are blanks. */
  text: string;
  blanks: string[];
}

export interface WordingPick {
  section: string;
  available: boolean;
  topics: WordingTopic[];
}

/** What the report already knows; the server fills matching blanks with it. */
export interface ClauseContext {
  commodity?: string;
  /** SEA or AIR, from the report type. */
  mode?: string;
  values: Record<string, string>;
  defects: string[];
}

export async function pickClauses(section: string, ctx: ClauseContext): Promise<WordingPick> {
  const res = await fetch('/api/clauses/pick', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({
      section,
      commodity: ctx.commodity || null,
      mode: ctx.mode || null,
      values: ctx.values,
      defects: ctx.defects,
    }),
  });
  if (!res.ok) {
    throw new Error(`Could not load the standard wording (${res.status}).`);
  }
  return res.json();
}


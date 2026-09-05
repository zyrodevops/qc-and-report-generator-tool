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
  block_state: any;
  created_at: string;
  updated_at: string;
}

export interface CreateReportParams {
  template_id: string;
  family?: string;
  year?: number;
  mode?: 'SEA' | 'AIR';
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

export async function login(email: string, password: string): Promise<UserSession> {
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Login failed' }));
    throw new Error(errorData.detail || 'Invalid email or password');
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
  const initialBlocks = [
    {
      id: 'b_particulars',
      type: 'particulars',
      rows: [
        { label: 'Applicant / Insurer', value: ['Marine Cargo Insurers Ltd.'] },
        { label: 'Declared Commodity', value: ['Fresh Citrus / Mandarins'] },
        { label: 'Transport Document', value: [params.mode === 'AIR' ? '098-12345675' : 'BL-CMAU-990123'] },
        { label: 'Place of Survey', value: ['CFS Cold Storage, Nhava Sheva'] },
      ],
    },
    {
      id: 'b_narrative',
      type: 'narrative',
      section: 'ATTENDANCE & CIRCUMSTANCES',
      additional_text: 'Survey conducted under normal ambient conditions at the cold store facility.',
      source: 'surveyor_entered',
    },
    {
      id: 'b_measurements',
      type: 'measurements',
      unit_system: 'metric',
      rows: [
        { subject: 'Pulp Temperature', method: 'Digital probe thermometer', min: '1.0', max: '1.4', unit: '°C' },
        { subject: 'Brix Level', method: 'Optical refractometer', min: '11.2', max: '12.0', unit: '%' },
      ],
    },
    {
      id: 'b_table',
      type: 'table',
      title: 'Defect Analysis Breakdown',
      unit: 'pcs',
      grouping_label: 'Count / Sample Size',
      categories: [
        { key: 'sound', label: 'Sound (Pcs)' },
        { key: 'soft', label: 'Soft (Pcs)' },
        { key: 'decay', label: 'Decay (Pcs)' },
        { key: 'bruised', label: 'Bruised (Pcs)' },
        { key: 'stem_rot', label: 'Stem Rot (Pcs)' },
      ],
      rows: [
        { group: 'Box Count 55', values: { sound: 133, soft: 54, decay: 14, bruised: 24, stem_rot: 9 } },
        { group: 'Box Count 65', values: { sound: 140, soft: 68, decay: 18, bruised: 13, stem_rot: 15 } },
      ],
    },
    {
      id: 'b_photo_plate',
      type: 'photo_plate',
      series_id: 'survey',
      label: 'Survey Photographs',
      provenance: 'own_survey',
      columns: 2,
      groups: [],
    },
    {
      id: 'b_fixed_text',
      type: 'fixed_text',
      key: 'disclaimer@v1',
      content: 'This report is issued without prejudice, subject to the conditions and limitations of carriage.',
    },
  ];

  const defaultState = {
    metadata: {
      number: 'ALLOCATED_BY_SERVER',
      family: params.family || 'QC_REPORT',
      state: 'DRAFT',
      template_id: params.template_id,
      template_version: 1,
      docx_template: 'mca-qc-v1.docx',
      status: 'DRAFT',
      issued_date: new Date().toISOString().split('T')[0],
      place: 'Mumbai, India',
    },
    transport: {
      mode: params.mode || 'SEA',
      document: {
        kind: params.mode === 'AIR' ? 'AIR_WAYBILL' : 'BILL_OF_LADING',
        number: params.mode === 'AIR' ? '098-12345675' : 'BL-990123',
        level: 'MASTER',
        check_digit_valid: true,
      },
      conveyances: [],
    },
    carriage_units: [
      {
        id: 'u1',
        unit_type: params.mode === 'AIR' ? 'ULD' : 'CONTAINER',
        identifier: params.mode === 'AIR' ? 'AKE12345AA' : 'CMAU2016593',
        identifier_valid: true,
      },
    ],
    weights: {
      gross_kg: '24500.00',
      net_kg: '22310.00',
    },
    blocks: initialBlocks,
    assets: {},
    provenance: {},
  };

  const res = await fetch('/api/reports', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify({
      template_id: params.template_id,
      family: params.family || 'QC_REPORT',
      year: params.year || 2026,
      block_state: params.block_state || defaultState,
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Failed to create report: ${err}`);
  }
  return res.json();
}

export async function updateBlockState(reportId: string, blockState: any): Promise<void> {
  const res = await fetch(`/api/reports/${reportId}/block-state`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify(blockState),
  });
  if (!res.ok) {
    throw new Error(`Failed to update report state: ${res.statusText}`);
  }
}

export function getDownloadDocxUrl(reportId: string): string {
  const token = getStoredToken();
  return `/api/reports/${reportId}/download/docx${token ? `?auth_token=${encodeURIComponent(token)}` : ''}`;
}

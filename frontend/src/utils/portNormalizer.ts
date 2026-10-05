import portsData from '../data/ports_data.json';

interface PortEntry {
  port: string;
  country: string;
  state?: string;
}

const COUNTRIES = new Set<string>((portsData.countries || []).map((c: string) => c.trim().toLowerCase()));
const PORTS_MAP: Record<string, PortEntry> = portsData.ports || {};

/**
 * Returns true if the port string already contains or ends with a known country.
 * e.g. "Navegantes, SC, Brazil" -> true, "Nhava Sheva" -> false.
 */
export function hasCountry(portStr: string): boolean {
  const s = (portStr || '').trim();
  if (!s || s.startsWith('[')) return true;

  const parts = s.split(',').map((p) => p.trim().toLowerCase()).filter(Boolean);
  if (parts.length >= 2) {
    const last = parts[parts.length - 1];
    if (COUNTRIES.has(last)) return true;
    for (const c of COUNTRIES) {
      if (new RegExp(`\\b${c}\\b`, 'i').test(last)) return true;
    }
  }

  const sLower = s.toLowerCase();
  for (const c of COUNTRIES) {
    if (sLower.endsWith(c)) {
      const pre = sLower.slice(0, -c.length).trimEnd();
      if (!pre || !/[a-z0-9]/i.test(pre.slice(-1)) || pre.endsWith(',') || pre.endsWith('-')) {
        return true;
      }
    }
  }

  return false;
}

/**
 * Normalizes a single port name using pre-seeded dictionary.
 * e.g. "Nhava Sheva" -> "Nhava Sheva, India"
 */
export function normalizePort(portStr: string): string {
  const s = (portStr || '').trim();
  if (!s || s.startsWith('[')) return s;

  if (hasCountry(s)) return s;

  const key = s.toLowerCase();
  const keyClean = key.replace(/\b(port of|terminal|cfs|port|icd)\b/gi, '').replace(/^[ ,.-]+|[ ,.-]+$/g, '');

  if (PORTS_MAP[key]) {
    const c = PORTS_MAP[key].country;
    if (!new RegExp(`\\b${c}\\b`, 'i').test(s)) return `${s}, ${c}`;
    return s;
  }

  if (PORTS_MAP[keyClean]) {
    const c = PORTS_MAP[keyClean].country;
    if (!new RegExp(`\\b${c}\\b`, 'i').test(s)) return `${s}, ${c}`;
    return s;
  }

  for (const [pKey, info] of Object.entries(PORTS_MAP)) {
    if (new RegExp(`\\b${pKey}\\b`, 'i').test(key)) {
      const c = info.country;
      if (!new RegExp(`\\b${c}\\b`, 'i').test(s)) return `${s}, ${c}`;
      return s;
    }
  }

  return s;
}

/**
 * Normalizes a full voyage string like "Navegantes, SC, Brazil to Nhava Sheva"
 * or "Navegantes to Nhava Sheva".
 */
export function normalizeVoyage(voyageStr: string): string {
  const s = (voyageStr || '').trim();
  if (!s || s.startsWith('[')) return s;

  if (/\s+to\s+/i.test(s)) {
    const parts = s.split(/\s+to\s+/i);
    const origin = normalizePort(parts[0].trim());
    const dest = normalizePort(parts.slice(1).join(' to ').trim());
    return `${origin} to ${dest}`;
  }

  return normalizePort(s);
}

/**
 * Asynchronously normalizes voyage using backend endpoint (which checks OpenStreetMap
 * for brand-new ports if not in local dictionary).
 */
export async function normalizeVoyageAsync(voyageStr: string): Promise<string> {
  const s = (voyageStr || '').trim();
  if (!s || s.startsWith('[')) return s;

  // First try synchronous local dictionary
  const localNormalized = normalizeVoyage(s);
  const parts = localNormalized.split(/\s+to\s+/i);
  const allHaveCountry = parts.every((p) => hasCountry(p.trim()));
  if (allHaveCountry) {
    return localNormalized;
  }

  // Fallback to backend API for online lookup
  try {
    const res = await fetch('/api/ports/normalize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ voyage: s }),
    });
    if (res.ok) {
      const data = await res.json();
      if (data?.normalized_voyage) {
        return data.normalized_voyage;
      }
    }
  } catch (err) {
    // Ignore network error and return best effort local normalization
  }

  return localNormalized;
}

/**
 * The client's private lists (staff and surveyors, cold storages).
 *
 * They hold real names, so they are not built into the site: the server sends
 * them only to a logged-in user (GET /api/reference-data). Until they arrive
 * (or if the server has none) the lists are empty and the form works as before
 * without suggestions. Components call useReferenceData() to re-render once
 * the lists have loaded.
 */
import { useEffect, useState } from 'react';
import { getAuthHeaders, getStoredToken } from '../api/client';

export interface StaffEntry {
  company?: string;
  name: string;
  designation: string;
  representing: string;
  line?: string;
}

export interface StaffSurveyorData {
  consignees: (StaffEntry & { company: string })[];
  shipping_lines: (StaffEntry & { line: string })[];
  shippers: StaffEntry[];
  cargo_insurers: StaffEntry[];
  mca_surveyors: StaffEntry[];
}

export interface ColdStorageLocation {
  id: string;
  city: string;
  name: string;
  clean_name: string;
  address: string;
}

const EMPTY_STAFF: StaffSurveyorData = {
  consignees: [],
  shipping_lines: [],
  shippers: [],
  cargo_insurers: [],
  mca_surveyors: [],
};

let staff: StaffSurveyorData = EMPTY_STAFF;
let coldStorages: ColdStorageLocation[] = [];
let licenceNo = '';
let loaded = false;
let pending: Promise<void> | null = null;
const listeners = new Set<() => void>();

export function getStaffData(): StaffSurveyorData {
  return staff;
}

export function getColdStorages(): ColdStorageLocation[] {
  return coldStorages;
}

/** The surveyor licence number printed in a survey report's closing ('' when the server has none). */
export function getLicenceNo(): string {
  return licenceNo;
}

export function referenceDataLoaded(): boolean {
  return loaded;
}

/** Fetches the lists once per page load; a failed try (e.g. not logged in yet) is retried next time. */
export function loadReferenceData(): Promise<void> {
  if (loaded) return Promise.resolve();
  if (pending) return pending;
  if (!getStoredToken()) return Promise.resolve();
  pending = fetch('/api/reference-data', { headers: getAuthHeaders() })
    .then(async (res) => {
      if (!res.ok) throw new Error(`reference data: HTTP ${res.status}`);
      const data = await res.json();
      staff = { ...EMPTY_STAFF, ...(data?.staff || {}) };
      coldStorages = Array.isArray(data?.cold_storages) ? data.cold_storages : [];
      licenceNo = typeof data?.licence_no === 'string' ? data.licence_no : '';
      loaded = true;
      listeners.forEach((fn) => fn());
    })
    .catch((err) => {
      console.warn('Could not load the staff and cold storage lists:', err);
    })
    .finally(() => {
      pending = null;
    });
  return pending;
}

/** True once the lists have arrived; the component re-renders then. */
export function useReferenceData(): boolean {
  const [ready, setReady] = useState(loaded);
  useEffect(() => {
    const onLoad = () => setReady(true);
    listeners.add(onLoad);
    if (loaded) setReady(true);
    else loadReferenceData();
    return () => {
      listeners.delete(onLoad);
    };
  }, []);
  return ready;
}

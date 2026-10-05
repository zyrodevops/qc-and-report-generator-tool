import React, { useState, useMemo, useRef, useEffect } from 'react';
import { Search, MapPin, Building2, Check, X, Sparkles } from 'lucide-react';
import { ColdStorageLocation, getColdStorages, useReferenceData } from '../../utils/referenceData';

export type { ColdStorageLocation } from '../../utils/referenceData';

export interface ColdStorageSelectorProps {
  currentText: string;
  onUpdateText: (updatedText: string) => void;
}

/**
 * Updates the Application text by replacing [Cold Storage Name] and [Cold Storage Address],
 * or replacing an existing M/s ... (...) reference with the chosen cold storage facility.
 */
export function applyColdStorageToText(currentText: string, loc: ColdStorageLocation): string {
  const facilityName = loc.clean_name || loc.name;
  const facilityAddress = loc.address;

  // 0. If text is empty or blank, build full sentence
  if (!currentText.trim()) {
    return `Pursuant to the Consignee's request and subsequent appointment, we attended the Consignee's nominated cold storage facility, M/s ${facilityName} (${facilityAddress}), on [Survey Date], to carry out an inspection of the subject consignment.`;
  }

  // 1. Direct placeholder replacement
  if (currentText.includes('[Cold Storage Name]') && currentText.includes('[Cold Storage Address]')) {
    return currentText
      .replace('[Cold Storage Name]', facilityName)
      .replace('[Cold Storage Address]', facilityAddress);
  }
  if (currentText.includes('[Cold Storage Name]')) {
    return currentText.replace('[Cold Storage Name]', `${facilityName} (${facilityAddress})`);
  }

  // 2. Pattern: "M/s <Name> (<Address>)"
  const msRegex = /(M\/s\s+)[^(\n]+(?:\s*\([^)]*\))?/i;
  if (msRegex.test(currentText)) {
    return currentText.replace(msRegex, `$1${facilityName} (${facilityAddress})`);
  }

  // 3. Pattern: "cold storage facility, M/s ..."
  const facilityRegex = /(cold storage facility,?\s*)(?:M\/s\s+)?[^,(\n]+(?:\s*\([^)]*\))?/i;
  if (facilityRegex.test(currentText)) {
    return currentText.replace(facilityRegex, `$1M/s ${facilityName} (${facilityAddress})`);
  }

  // 4. Fallback: prepend facility info or return text
  return currentText;
}

export const ColdStorageSelector: React.FC<ColdStorageSelectorProps> = ({ currentText, onUpdateText }) => {
  // Re-renders with the list once it has arrived from the server.
  useReferenceData();
  const locations: ColdStorageLocation[] = getColdStorages();
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Filter locations by search query (across name, clean_name, address, city)
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return locations.slice(0, 30); // show top 30 by default
    return locations.filter(
      (loc) =>
        loc.name.toLowerCase().includes(q) ||
        loc.clean_name.toLowerCase().includes(q) ||
        loc.address.toLowerCase().includes(q) ||
        loc.city.toLowerCase().includes(q)
    );
  }, [locations, query]);

  // Detect if text already contains any known cold storage name whose address isn't filled yet
  const inlineDetected = useMemo(() => {
    if (!currentText) return null;
    const lower = currentText.toLowerCase();
    for (const loc of locations) {
      const searchTarget = (loc.clean_name || loc.name).toLowerCase();
      if (searchTarget.length > 5 && lower.includes(searchTarget)) {
        // If the address is already in the text, no need to suggest
        const addrSnippet = loc.address.slice(0, 25).toLowerCase();
        if (!lower.includes(addrSnippet)) {
          return loc;
        }
      }
    }
    return null;
  }, [currentText, locations]);

  const handleSelect = (loc: ColdStorageLocation) => {
    const nextText = applyColdStorageToText(currentText, loc);
    onUpdateText(nextText);
    setQuery('');
    setIsOpen(false);
  };

  return (
    <div ref={containerRef} className="relative mb-2">
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <div className="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-slate-400">
            <Building2 size={13} className="text-blue-600" />
          </div>
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setIsOpen(true);
            }}
            onFocus={() => setIsOpen(true)}
            placeholder={`Search cold storage to auto-fill address (${locations.length} registered locations in Mumbai, Pune, Delhi, etc.)…`}
            className="w-full pl-7 pr-7 py-1 text-xs border border-slate-300 rounded-md bg-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 placeholder:text-slate-400 text-slate-700"
          />
          {query && (
            <button
              type="button"
              onClick={() => {
                setQuery('');
                setIsOpen(false);
              }}
              className="absolute inset-y-0 right-0 pr-2 flex items-center text-slate-400 hover:text-slate-600 cursor-pointer"
            >
              <X size={12} />
            </button>
          )}
        </div>
      </div>

      {/* Auto-detected match suggestion banner if user typed the name directly in the textarea */}
      {inlineDetected && !isOpen && (
        <div className="mt-1.5 flex items-center justify-between gap-2 px-2.5 py-1 text-[11px] bg-blue-50/80 border border-blue-200 rounded-md text-blue-900 animate-fade-in">
          <div className="flex items-center gap-1.5 truncate">
            <Sparkles size={12} className="text-blue-600 shrink-0" />
            <span className="truncate">
              Detected <strong>{inlineDetected.clean_name || inlineDetected.name}</strong>. Auto-fill address?
            </span>
          </div>
          <button
            type="button"
            onClick={() => handleSelect(inlineDetected)}
            className="shrink-0 px-2 py-0.5 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium text-[10px] cursor-pointer transition shadow-2xs"
          >
            Fill Address
          </button>
        </div>
      )}

      {/* Autocomplete Dropdown */}
      {isOpen && (
        <div className="absolute left-0 right-0 top-full mt-1 z-50 bg-white border border-slate-200 rounded-lg shadow-lg max-h-64 overflow-y-auto divide-y divide-slate-100">
          <div className="px-2.5 py-1 bg-slate-50 text-[10px] font-semibold text-slate-500 flex justify-between items-center border-b border-slate-200">
            <span>Registered Cold Storage Facilities ({filtered.length} found)</span>
            <span>Click to insert Name & Address</span>
          </div>
          {filtered.length === 0 ? (
            <div className="p-3 text-center text-xs text-slate-400">
              No matching cold storage facility found. You can still type custom details directly into the text box.
            </div>
          ) : (
            filtered.map((loc) => (
              <button
                key={loc.id}
                type="button"
                onClick={() => handleSelect(loc)}
                className="w-full text-left px-3 py-1.5 hover:bg-blue-50/80 transition flex items-start justify-between gap-2 cursor-pointer group"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-xs text-slate-800 group-hover:text-blue-700">
                      {loc.name}
                    </span>
                    <span className="text-[9px] uppercase px-1.5 py-0.2 bg-slate-100 text-slate-600 rounded border border-slate-200">
                      {loc.city}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-500 truncate mt-0.5 flex items-center gap-1">
                    <MapPin size={10} className="shrink-0 text-slate-400" />
                    <span className="truncate">{loc.address}</span>
                  </div>
                </div>
                <span className="text-[10px] text-blue-600 opacity-0 group-hover:opacity-100 font-medium whitespace-nowrap self-center">
                  Select ↵
                </span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
};

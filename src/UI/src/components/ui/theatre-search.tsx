import { useState, useEffect, useRef } from 'react';
import { Building2, Search, Plus, X, Loader2, MapPin } from 'lucide-react';
import { authenticatedFetch } from '../../utils/api';

export interface TheatreItem {
  name: string;
  thumbnail: string;
  location: string;
  category: string;
  entity_code: string;
  bms_url: string;
}

interface TheatreSearchProps {
  regionCode?: string;
  regionSlug?: string;
  lat?: string;
  lon?: string;
  geohash?: string;
  selectedTheatres: string[];
  onChangeTheatres: (theatres: string[]) => void;
}

/**
 * Provides a searchable interface for adding and removing theatres for a region.
 *
 * @param selectedTheatres - The currently selected theatre names.
 * @param onChangeTheatres - Callback invoked with the updated theatre selection.
 * @param regionCode - Region code used for theatre searches.
 * @param regionSlug - Region slug used for theatre searches.
 * @param lat - Latitude used for theatre searches.
 * @param lon - Longitude used for theatre searches.
 * @param geohash - Geohash used for theatre searches.
 */
export function TheatreSearch({
  regionCode = 'CHEN',
  regionSlug = 'chennai',
  lat = '13.056',
  lon = '80.206',
  geohash = 'tf3',
  selectedTheatres,
  onChangeTheatres,
}: TheatreSearchProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<TheatreItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Reset search when region changes
  useEffect(() => {
    setQuery('');
    setResults([]);
    setIsOpen(false);
  }, [regionCode]);

  // Debounced search API call
  useEffect(() => {
    if (!query.trim() || query.trim().length < 2) {
      setResults([]);
      setLoading(false);
      return;
    }

    let isSubscribed = true;
    setLoading(true);
    const handler = setTimeout(() => {
      const queryParams = new URLSearchParams({
        q: query.trim(),
        region: regionCode,
        regionSlug: regionSlug,
        lat: lat,
        lon: lon,
        geohash: geohash,
      });

      authenticatedFetch(`/api/bms/search/theatres?${queryParams.toString()}`)
        .then(async (res) => {
          if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || `Search failed with status ${res.status}`);
          }
          return res.json();
        })
        .then((data) => {
          if (isSubscribed) {
            setResults(data.results || []);
            setLoading(false);
            setIsOpen(true);
          }
        })
        .catch((err) => {
          if (isSubscribed) {
            console.error("Theatre search error:", err);
            setResults([]);
            setLoading(false);
          }
        });
    }, 300);

    return () => {
      isSubscribed = false;
      clearTimeout(handler);
    };
  }, [query, regionCode, regionSlug, lat, lon, geohash]);

  const handleAddTheatre = (name: string) => {
    const cleanName = name.trim();
    if (!cleanName) return;
    if (!selectedTheatres.some(t => t.toLowerCase() === cleanName.toLowerCase())) {
      onChangeTheatres([...selectedTheatres, cleanName]);
    }
    setQuery('');
    setIsOpen(false);
  };

  const handleRemoveTheatre = (indexToRemove: number) => {
    onChangeTheatres(selectedTheatres.filter((_, idx) => idx !== indexToRemove));
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (query.trim()) {
        handleAddTheatre(query.trim());
      }
    }
  };

  return (
    <div className="space-y-3" ref={dropdownRef}>
      <label className="font-bold text-muted-foreground uppercase tracking-wider text-[10px] flex items-center justify-between">
        <span className="flex items-center gap-1">
          <Building2 className="h-3 w-3 text-rose-500" />
          Target Cinemas / Theatres 🏢
        </span>
        <span className="text-[10px] text-muted-foreground">
          {selectedTheatres.length} added
        </span>
      </label>

      {/* Search Input Box */}
      <div className="relative">
        <Search className="h-4 w-4 absolute left-3.5 top-3 text-muted-foreground pointer-events-none" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => { if (query.trim().length >= 2) setIsOpen(true); }}
          placeholder="Search and add cinema (e.g. Nexus, PVR ECX)..."
          className="w-full h-10 pl-10 pr-10 bg-muted/20 border border-border/80 rounded-xl text-xs focus:outline-none focus:border-rose-500/40 font-medium"
        />
        {loading ? (
          <Loader2 className="h-4 w-4 absolute right-3 top-3 text-rose-500 animate-spin" />
        ) : query ? (
          <button
            type="button"
            onClick={() => handleAddTheatre(query)}
            className="absolute right-2 top-2 p-1 rounded-lg bg-rose-500/20 text-rose-400 hover:bg-rose-500/30 transition-colors cursor-pointer"
            title="Add typed cinema name"
          >
            <Plus className="h-3.5 w-3.5" />
          </button>
        ) : null}

        {/* Dynamic Search Dropdown Results */}
        {isOpen && (
          <div className="absolute top-11 left-0 right-0 z-50 bg-slate-900 border border-border/80 rounded-xl shadow-2xl p-2 max-h-60 overflow-y-auto space-y-1 custom-scrollbar animate-in fade-in duration-150">
            {results.length > 0 ? (
              results.map((item, idx) => {
                const isAlreadyAdded = selectedTheatres.some(t => t.toLowerCase() === item.name.toLowerCase());
                return (
                  <button
                    key={idx}
                    type="button"
                    disabled={isAlreadyAdded}
                    onClick={() => !isAlreadyAdded && handleAddTheatre(item.name)}
                    className={`w-full text-left p-2 rounded-lg flex items-center justify-between gap-3 text-xs transition-colors ${
                      isAlreadyAdded
                        ? 'bg-muted/20 opacity-50 cursor-not-allowed'
                        : 'hover:bg-rose-500/10 hover:text-rose-400 cursor-pointer'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      {item.thumbnail ? (
                        <img src={item.thumbnail} alt="" className="h-8 w-8 rounded object-cover shrink-0 bg-black/40" />
                      ) : (
                        <div className="h-8 w-8 rounded bg-muted/40 flex items-center justify-center shrink-0">
                          <Building2 className="h-4 w-4 text-muted-foreground" />
                        </div>
                      )}
                      <div className="min-w-0">
                        <p className="font-bold truncate text-foreground/90">{item.name}</p>
                        {item.location && (
                          <p className="text-[10px] text-muted-foreground truncate flex items-center gap-0.5">
                            <MapPin className="h-2.5 w-2.5 shrink-0" />
                            {item.location}
                          </p>
                        )}
                      </div>
                    </div>

                    {isAlreadyAdded ? (
                      <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full shrink-0">Added</span>
                    ) : (
                      <span
                        className="text-[10px] font-bold bg-rose-500/20 text-rose-400 px-2.5 py-1 rounded-md hover:bg-rose-500/30 transition-colors shrink-0 flex items-center gap-1"
                      >
                        <Plus className="h-3 w-3" />
                        Add
                      </span>
                    )}
                  </button>
                );
              })
            ) : !loading && query.trim().length >= 2 ? (
              <button
                type="button"
                onClick={() => handleAddTheatre(query)}
                className="w-full text-left p-3 rounded-lg text-xs text-rose-400 hover:bg-rose-500/10 transition-colors cursor-pointer flex items-center justify-between"
              >
                <div className="space-y-0.5">
                  <p className="font-bold">Add "{query.trim()}" as custom cinema</p>
                  <p className="text-[10px] text-muted-foreground">Not found in BookMyShow index — click to add custom name</p>
                </div>
                <Plus className="h-4 w-4 shrink-0" />
              </button>
            ) : null}
          </div>
        )}
      </div>


      {/* Selected Theatres Chips List */}
      {selectedTheatres.length > 0 ? (
        <div className="flex flex-wrap gap-2 p-2.5 bg-muted/10 border border-border/40 rounded-xl min-h-[44px]">
          {selectedTheatres.map((th, idx) => (
            <span
              key={idx}
              className="inline-flex items-center gap-1.5 bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs font-semibold px-2.5 py-1 rounded-lg animate-in zoom-in-75"
            >
              <span>{th}</span>
              <button
                type="button"
                onClick={() => handleRemoveTheatre(idx)}
                className="hover:text-white transition-colors cursor-pointer"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      ) : (
        <p className="text-[11px] text-muted-foreground italic px-1">
          No cinemas added yet. Search above to add cinemas one by one.
        </p>
      )}
    </div>
  );
}

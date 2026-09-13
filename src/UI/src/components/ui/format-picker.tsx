import { useState, useEffect } from 'react';
import { Layers, Loader2, AlertCircle, Check, Film } from 'lucide-react';
import { authenticatedFetch } from '../../utils/api';

export interface FormatOption {
  label: string;
  eventCode: string;
  eventUrl: string;
  refEventCode: string;
  language: string;
}

export interface FormatGroup {
  language: string;
  formats: FormatOption[];
}

export interface MovieFormatInfo {
  title?: string;
  runtime?: string;
  censor?: string;
  genre?: string;
  releaseDate?: string;
}

export interface ShowDateOption {
  dateCode: string;
  label: string;
  isDisabled: boolean;
}

export interface AvailableTheatre {
  name: string;
  code?: string;
}

interface FormatPickerProps {
  eventCode: string;
  movieTitle?: string;
  movieCtaUrl?: string;
  regionCode?: string;
  regionSlug?: string;
  lat?: string;
  lon?: string;
  geohash?: string;
  selectedFormat: FormatOption | null;
  onSelectFormat: (format: FormatOption) => void;
  onAvailableDatesFetched?: (dates: ShowDateOption[]) => void;
  onTheatresFetched?: (theatres: AvailableTheatre[]) => void;
}

/**
 * Fetches and displays selectable movie language and format options.
 *
 * Automatically selects the first available format and forwards fetched show dates when provided.
 *
 * @param eventCode - The movie event code used to load format options.
 * @param movieCtaUrl - URL used to derive a missing format event URL.
 * @param selectedFormat - The currently selected format.
 * @param onSelectFormat - Called when a format is selected.
 * @param onAvailableDatesFetched - Called when show dates are available.
 * @returns The format picker interface, or `null` when no event code is provided.
 */
export function FormatPicker({
  eventCode,
  movieTitle: _movieTitle,
  movieCtaUrl,
  regionCode = 'CHEN',
  regionSlug = 'chennai',
  lat = '13.056',
  lon = '80.206',
  geohash = 'tf3',
  selectedFormat,
  onSelectFormat,
  onAvailableDatesFetched,
  onTheatresFetched,
}: FormatPickerProps) {
  const [groups, setGroups] = useState<FormatGroup[]>([]);
  const [movieInfo, setMovieInfo] = useState<MovieFormatInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!eventCode) {
      setGroups([]);
      return;
    }

    let isMounted = true;
    setLoading(true);
    setError(null);

    const queryParams = new URLSearchParams({
      eventCode,
      region: regionCode,
      regionSlug: regionSlug,
      lat: lat,
      lon: lon,
      geohash: geohash,
    });

    authenticatedFetch(`/api/bms/movie-formats?${queryParams.toString()}`)
      .then(async (res) => {
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || 'Failed to fetch format options');
        }
        return res.json();
      })
      .then((data) => {
        if (!isMounted) return;
        const fetchedGroups: FormatGroup[] = data.groups || [];
        setGroups(fetchedGroups);
        setMovieInfo(data.movieInfo || null);

        if (data.showDates && data.showDates.length > 0 && onAvailableDatesFetched) {
          onAvailableDatesFetched(data.showDates);
        }

        if (data.theatres && Array.isArray(data.theatres) && onTheatresFetched) {
          onTheatresFetched(data.theatres);
        }

        // Auto-select first format if none currently selected
        if (fetchedGroups.length > 0) {
          const firstFormat = fetchedGroups[0].formats[0];
          if (firstFormat) {
            const effectiveFormat = enrichFormatUrl(firstFormat, movieCtaUrl);
            onSelectFormat(effectiveFormat);
          }
        }
        setLoading(false);
      })
      .catch((err) => {
        if (isMounted) {
          console.error("FormatPicker fetch error:", err);
          setError(err.message || 'Could not load formats');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [eventCode, movieCtaUrl, regionCode, regionSlug, lat, lon, geohash, onSelectFormat, onAvailableDatesFetched, onTheatresFetched]);

  const enrichFormatUrl = (fmt: FormatOption, ctaUrl?: string): FormatOption => {
    if (fmt.eventUrl) return fmt;
    let derivedSlug = '';
    if (ctaUrl) {
      const parts = ctaUrl.split('?')[0].split('/').filter(Boolean);
      const codeIdx = parts.findIndex(p => /^ET\d{8}$/i.test(p));
      if (codeIdx > 0) {
        derivedSlug = parts[codeIdx - 1];
      } else if (parts.length >= 2) {
        derivedSlug = parts[parts.length - 1];
      }
    }
    return {
      ...fmt,
      eventUrl: derivedSlug || 'movie'
    };
  };

  if (!eventCode) return null;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="font-bold text-muted-foreground uppercase tracking-wider text-[10px] flex items-center gap-1">
          <Layers className="h-3 w-3 text-rose-500" />
          Select Language & Format 🎧
        </label>
        {movieInfo?.runtime && (
          <span className="text-[10px] text-muted-foreground/80 font-medium flex items-center gap-1">
            <Film className="h-3 w-3 text-rose-400" />
            {movieInfo.runtime}
          </span>
        )}
      </div>

      {loading ? (
        <div className="h-16 border border-border/50 bg-muted/10 rounded-xl flex items-center justify-center space-x-2">
          <Loader2 className="h-4 w-4 text-rose-500 animate-spin mr-2" />
          <span className="text-xs text-muted-foreground">Loading movie formats...</span>
        </div>
      ) : error ? (
        <div className="p-3 border border-amber-500/30 bg-amber-500/10 rounded-xl text-xs text-amber-400 flex items-center gap-2">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      ) : groups.length === 0 ? (
        <div className="p-3 border border-border/50 bg-muted/10 rounded-xl text-xs text-muted-foreground text-center">
          Standard format will be used for monitoring.
        </div>
      ) : (
        <div className="space-y-2.5 bg-muted/10 border border-border/60 p-3 rounded-xl">
          {groups.map((group, gIdx) => (
            <div key={gIdx} className="space-y-1.5">
              <span className="text-[11px] font-bold text-foreground/80 tracking-wide block">
                {group.language}
              </span>
              <div className="flex flex-wrap gap-1.5">
                {group.formats.map((fmt, fIdx) => {
                  const enriched = enrichFormatUrl(fmt, movieCtaUrl);
                  const isSelected =
                    selectedFormat?.eventCode === enriched.eventCode &&
                    selectedFormat?.language === enriched.language &&
                    selectedFormat?.label === enriched.label;

                  return (
                    <button
                      key={fIdx}
                      type="button"
                      onClick={() => onSelectFormat(enriched)}
                      className={`text-xs px-3 py-1.5 rounded-lg border font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
                        isSelected
                          ? 'border-rose-500 bg-rose-500/20 text-rose-400 ring-1 ring-rose-500/50 shadow-sm'
                          : 'border-border/70 bg-background/50 text-muted-foreground hover:border-rose-500/40 hover:text-foreground'
                      }`}
                    >
                      {isSelected && <Check className="h-3 w-3 text-rose-400" />}
                      <span>{enriched.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

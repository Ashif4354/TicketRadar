import { useState, useEffect, useMemo } from 'react';
import { Film, MapPin, Check, Search, AlertCircle, Loader2 } from 'lucide-react';
import { authenticatedFetch } from '../../utils/api';
import citiesData from '../../assets/cities.json';

export interface CityEntry {
  RegionCode: string;
  RegionName: string;
  RegionSlug: string;
  Lat: string;
  Long: string;
  GeoHash: string;
  StateName?: string;
}

export interface MovieItem {
  title: string;
  poster: string;
  rating: string;
  genres: string[];
  languages: string;
  ctaUrl: string;
  eventCode?: string;
}

interface MoviePickerProps {
  selectedCity: CityEntry | null;
  onCityChange: (city: CityEntry) => void;
  selectedMovieUrl: string;
  onSelectMovie: (ctaUrl: string, title: string, eventCode?: string) => void;
}

/**
 * Provides city selection and movie browsing for the selected region.
 *
 * @param selectedCity - The currently selected city, or `null` when none is selected.
 * @param onCityChange - Called when a city is selected or the default city is assigned.
 * @param selectedMovieUrl - URL of the movie currently selected.
 * @param onSelectMovie - Called when a movie is selected.
 */
export function MoviePicker({
  selectedCity,
  onCityChange,
  selectedMovieUrl,
  onSelectMovie,
}: MoviePickerProps) {
  const allCities = useMemo<CityEntry[]>(() => {
    try {
      const top = (citiesData as any)?.BookMyShow?.TopCities || [];
      const other = (citiesData as any)?.BookMyShow?.OtherCities || [];
      const combined = [...top, ...other];
      const seen = new Set<string>();
      const result: CityEntry[] = [];
      for (const c of combined) {
        const code = c.RegionCode || c.SubRegionCode || c.RegionSlug;
        if (code && !seen.has(String(code).toUpperCase())) {
          seen.add(String(code).toUpperCase());
          result.push({
            RegionCode: String(c.RegionCode || c.SubRegionCode || code),
            RegionName: String(c.RegionName || c.SubRegionName || "City"),
            RegionSlug: String(c.RegionSlug || c.SubRegionSlug || "city"),
            Lat: String(c.Lat || "19.076"),
            Long: String(c.Long || "72.8777"),
            GeoHash: String(c.GeoHash || "te7"),
            StateName: c.StateName ? String(c.StateName) : ""
          });
        }
      }
      return result;
    } catch {
      return [];
    }
  }, []);

  const [citySearch, setCitySearch] = useState('');
  const [isCityOpen, setIsCityOpen] = useState(false);
  const [movies, setMovies] = useState<MovieItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Set default city (e.g., Chennai or Mumbai) on mount if none selected
  useEffect(() => {
    if (!selectedCity && allCities.length > 0) {
      const defaultCity = allCities.find(c => c.RegionCode === 'CHEN') || allCities[0];
      onCityChange(defaultCity);
    }
  }, [allCities, selectedCity, onCityChange]);

  // Fetch movies whenever selected city changes
  useEffect(() => {
    if (!selectedCity) return;
    let isMounted = true;
    setLoading(true);
    setError(null);

    const queryParams = new URLSearchParams({
      region: selectedCity.RegionCode,
      regionSlug: selectedCity.RegionSlug,
      lat: selectedCity.Lat,
      lon: selectedCity.Long,
      geohash: selectedCity.GeoHash,
    });

    authenticatedFetch(`/api/bms/movies?${queryParams.toString()}`)
      .then(async (res) => {
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || 'Failed to fetch movies');
        }
        return res.json();
      })
      .then((data) => {
        if (isMounted) {
          setMovies(data.movies || []);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          logger_error(err);
          setError(err.message || 'Could not load movies');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [selectedCity]);

  const filteredCities = useMemo(() => {
    if (!citySearch.trim()) return allCities.slice(0, 50);
    return allCities.filter((c: CityEntry) => 
      c.RegionName.toLowerCase().includes(citySearch.toLowerCase()) ||
      c.StateName?.toLowerCase().includes(citySearch.toLowerCase()) ||
      c.RegionCode.toLowerCase().includes(citySearch.toLowerCase())
    ).slice(0, 100);
  }, [allCities, citySearch]);


  const helper_clean_image = (url: string) => {
    if (!url) return '';
    return url.replace('http://', 'https://');
  };

  return (
    <div className="space-y-4">
      {/* City Selection Bar */}
      <div className="space-y-1.5 relative">
        <label className="font-bold text-muted-foreground uppercase tracking-wider text-[10px] flex items-center justify-between">
          <span className="flex items-center gap-1">
            <MapPin className="h-3 w-3 text-rose-500" />
            Select City / Region
          </span>
          {selectedCity && (
            <span className="text-[10px] text-rose-400 font-semibold">
              {selectedCity.RegionName} ({selectedCity.RegionCode})
            </span>
          )}
        </label>

        {/* Dropdown Selector */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setIsCityOpen(!isCityOpen)}
            className="w-full h-10 px-3.5 rounded-xl border border-border/80 bg-muted/20 hover:border-rose-500/40 text-left text-xs font-semibold flex items-center justify-between transition-all cursor-pointer"
          >
            <span className="flex items-center gap-2 truncate">
              <MapPin className="h-4 w-4 text-rose-500 shrink-0" />
              {selectedCity ? (
                <span>
                  {selectedCity.RegionName}
                  {selectedCity.StateName && <span className="text-muted-foreground ml-1 font-normal">({selectedCity.StateName})</span>}
                </span>
              ) : (
                <span className="text-muted-foreground">Select a city...</span>
              )}
            </span>
            <Search className="h-3.5 w-3.5 text-muted-foreground" />
          </button>

          {isCityOpen && (
            <div className="absolute top-11 left-0 right-0 z-50 bg-slate-900 border border-border/80 rounded-xl shadow-2xl p-2 space-y-2 animate-in fade-in duration-150">
              <div className="relative">
                <Search className="h-3.5 w-3.5 absolute left-3 top-2.5 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Search city..."
                  value={citySearch}
                  onChange={(e) => setCitySearch(e.target.value)}
                  className="w-full h-8 pl-8 pr-3 bg-muted/30 border border-border/50 rounded-lg text-xs focus:outline-none focus:border-rose-500/40"
                  autoFocus
                />
              </div>

              <div className="max-h-48 overflow-y-auto space-y-0.5 custom-scrollbar">
                {filteredCities.length === 0 ? (
                  <p className="p-3 text-[11px] text-muted-foreground text-center">No city found</p>
                ) : (
                  filteredCities.map((city) => (
                    <button
                      key={city.RegionCode}
                      type="button"
                      onClick={() => {
                        onCityChange(city);
                        setIsCityOpen(false);
                        setCitySearch('');
                      }}
                      className={`w-full text-left px-3 py-2 rounded-lg text-xs flex items-center justify-between hover:bg-rose-500/10 hover:text-rose-400 transition-colors cursor-pointer ${
                        selectedCity?.RegionCode === city.RegionCode ? 'bg-rose-500/15 text-rose-400 font-bold' : 'text-foreground/90'
                      }`}
                    >
                      <span>{city.RegionName}</span>
                      {selectedCity?.RegionCode === city.RegionCode && (
                        <Check className="h-3.5 w-3.5 text-rose-500" />
                      )}
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Movies Cards Grid */}
      <div className="space-y-1.5">
        <label className="font-bold text-muted-foreground uppercase tracking-wider text-[10px] flex items-center gap-1">
          <Film className="h-3 w-3 text-rose-500" />
          Select Movie in {selectedCity?.RegionName || 'City'} 🎬
        </label>

        {loading ? (
          <div className="h-44 border border-border/50 bg-muted/10 rounded-xl flex flex-col items-center justify-center space-y-2">
            <Loader2 className="h-6 w-6 text-rose-500 animate-spin" />
            <p className="text-xs text-muted-foreground font-medium">Fetching movies from BookMyShow...</p>
          </div>
        ) : error ? (
          <div className="p-4 border border-destructive/30 bg-destructive/10 rounded-xl text-xs text-destructive flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        ) : movies.length === 0 ? (
          <div className="p-6 border border-border/50 bg-muted/10 rounded-xl text-center text-xs text-muted-foreground">
            No active movies found for {selectedCity?.RegionName}. Try selecting another city.
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 max-h-72 overflow-y-auto p-1 custom-scrollbar">
            {movies.map((movie, idx) => {
              const isSelected = selectedMovieUrl === movie.ctaUrl;
              return (
                <div
                  key={idx}
                  onClick={() => onSelectMovie(movie.ctaUrl, movie.title, movie.eventCode)}
                  className={`group relative rounded-xl border p-2.5 flex flex-col justify-between transition-all cursor-pointer hover:shadow-lg ${
                    isSelected
                      ? 'border-rose-500 bg-rose-500/10 ring-2 ring-rose-500/30'
                      : 'border-border/60 bg-muted/10 hover:border-rose-500/40 hover:bg-muted/20'
                  }`}
                >
                  {/* Selected Indicator */}
                  {isSelected && (
                    <div className="absolute top-2 right-2 z-10 h-5 w-5 rounded-full bg-rose-500 text-white flex items-center justify-center shadow-md animate-in zoom-in-50">
                      <Check className="h-3 w-3 stroke-[3]" />
                    </div>
                  )}

                  {/* Poster Image */}
                  <div className="aspect-[2/3] w-full rounded-lg overflow-hidden bg-black/40 mb-2 relative">
                    {movie.poster ? (
                      <img
                        src={helper_clean_image(movie.poster)}
                        alt={movie.title}
                        className="h-full w-full object-cover group-hover:scale-105 transition-transform duration-300"
                        loading="lazy"
                      />
                    ) : (
                      <div className="h-full w-full flex items-center justify-center text-muted-foreground">
                        <Film className="h-8 w-8 opacity-40" />
                      </div>
                    )}
                    {movie.rating && (
                      <span className="absolute bottom-1 left-1 bg-black/80 backdrop-blur-md text-[9px] font-bold px-1.5 py-0.5 rounded text-rose-300 border border-white/10">
                        {movie.rating}
                      </span>
                    )}
                  </div>

                  {/* Title & Language */}
                  <div className="space-y-1">
                    <h5 className="text-xs font-bold line-clamp-1 text-foreground group-hover:text-rose-400 transition-colors">
                      {movie.title}
                    </h5>
                    {movie.languages && (
                      <p className="text-[10px] text-muted-foreground line-clamp-1">
                        {movie.languages}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function logger_error(err: any) {
  console.error("MoviePicker Error:", err);
}

import { FormEvent, useEffect, useRef, useState } from 'react';
import { CloudSun, LoaderCircle, MapPinned, Search } from 'lucide-react';
import { HeroTemperature } from './components/HeroTemperature';
import { AiCommentTop } from './components/AiCommentTop';
import { HourlyForecast } from './components/HourlyForecast';
import { DailyForecast } from './components/DailyForecast';
import { ActivityPanel } from './components/ActivityPanel';
import { WeatherHighlights } from './components/WeatherHighlights';
import { AlertBanner } from './components/AlertBanner';
import { OutfitPlanCard } from './components/OutfitPlanCard';
import {
  fetchDashboard,
  fetchLocationSuggestions,
  type DashboardResponse,
  type LocationSuggestion,
  type SavedLocation,
} from './lib/api';

const STORAGE_KEY = 'weatherwise.selected-location';
const FAVORITES_KEY = 'weatherwise.favorite-locations';
const LEGACY_CURRENT_LOCATION_LABELS = new Set(['Mevcut Konum', 'Current Location']);

function App() {
  const [selectedLocation, setSelectedLocation] = useState<SavedLocation | null>(readStoredLocation);
  const [draftCity, setDraftCity] = useState(() => {
    const stored = readStoredLocation();
    return getLocationLabel(stored ?? { kind: 'city', city: 'Istanbul' });
  });
  const [favoriteLocations, setFavoriteLocations] = useState<SavedLocation[]>(readStoredFavorites);
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [locating, setLocating] = useState(() => readStoredLocation() === null && Boolean(navigator.geolocation));
  const [fetchedSuggestions, setFetchedSuggestions] = useState<LocationSuggestion[]>([]);
  const [fetchedSuggestionsQuery, setFetchedSuggestionsQuery] = useState('');
  const [pendingSearchQuery, setPendingSearchQuery] = useState<string | null>(null);
  const [suggestionsOpen, setSuggestionsOpen] = useState(false);
  const [hasSearchInteraction, setHasSearchInteraction] = useState(false);
  const searchBoxRef = useRef<HTMLDivElement>(null);
  const [locationSearchCache, setLocationSearchCache] = useState<Record<string, LocationSuggestion[]>>({});
  const activeSearchControllerRef = useRef<AbortController | null>(null);
  const skipSuggestionsRef = useRef(false);

  useEffect(() => {
    if (selectedLocation) return;

    if (!navigator.geolocation) {
      Promise.resolve().then(() => setSelectedLocation({ kind: 'city', city: 'Istanbul' }));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const next: SavedLocation = {
          kind: 'coords',
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          label: 'Current Location',
        };
        safeSetStorageItem(STORAGE_KEY, JSON.stringify(next));
        setDraftCity('Current Location');
        setSelectedLocation(next);
        setLocating(false);
      },
      () => {
        setSelectedLocation({ kind: 'city', city: 'Istanbul' });
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 },
    );
  }, [selectedLocation]);

  useEffect(() => {
    if (!selectedLocation) return;
    const currentLocation = selectedLocation;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const next = await fetchDashboard(currentLocation);
        if (!cancelled) {
          setData(next);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Something went wrong.');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [selectedLocation]);

  useEffect(() => {
    const query = draftCity.trim();
    const normalizedQuery = query.toLowerCase();

    if (skipSuggestionsRef.current) {
      skipSuggestionsRef.current = false;
      return;
    }

    if (query.length < 2 || LEGACY_CURRENT_LOCATION_LABELS.has(query)) {
      activeSearchControllerRef.current?.abort();
      return;
    }

    const cached = locationSearchCache[normalizedQuery];
    if (cached) {
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(async () => {
      activeSearchControllerRef.current?.abort();
      const controller = new AbortController();
      activeSearchControllerRef.current = controller;
      setPendingSearchQuery(normalizedQuery);
      try {
        const results = await fetchLocationSuggestions(query, controller.signal);
        if (!cancelled) {
          setLocationSearchCache((prev) => ({ ...prev, [normalizedQuery]: results }));
          setFetchedSuggestionsQuery(normalizedQuery);
          setFetchedSuggestions(results);
        }
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') {
          return;
        }
        if (!cancelled) {
          setFetchedSuggestionsQuery(normalizedQuery);
          setFetchedSuggestions([]);
        }
      } finally {
        if (!cancelled) {
          setPendingSearchQuery(null);
        }
      }
    }, 220);

    return () => {
      cancelled = true;
      activeSearchControllerRef.current?.abort();
      window.clearTimeout(timer);
    };
  }, [draftCity, locationSearchCache]);

  const searchQuery = draftCity.trim();
  const normalizedSearchQuery = searchQuery.toLowerCase();
  const isSearchableQuery = searchQuery.length >= 2 && !LEGACY_CURRENT_LOCATION_LABELS.has(searchQuery);
  const cachedSuggestions = isSearchableQuery
    ? (locationSearchCache[normalizedSearchQuery] ?? [])
    : [];
  const activeSuggestions = cachedSuggestions.length > 0
    ? cachedSuggestions
    : (fetchedSuggestionsQuery === normalizedSearchQuery ? fetchedSuggestions : []);
  const searchingLocations = isSearchableQuery && pendingSearchQuery === normalizedSearchQuery;
  const hasSearchAttempt = isSearchableQuery && (
    Object.prototype.hasOwnProperty.call(locationSearchCache, normalizedSearchQuery)
    || fetchedSuggestionsQuery === normalizedSearchQuery
  );

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (!searchBoxRef.current?.contains(event.target as Node)) {
        setSuggestionsOpen(false);
      }
    }

    window.addEventListener('mousedown', handleClickOutside);
    return () => window.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextCity = draftCity.trim();
    if (nextCity) {
      skipSuggestionsRef.current = true;
      const next: SavedLocation = { kind: 'city', city: nextCity };
      safeSetStorageItem(STORAGE_KEY, JSON.stringify(next));
      setSelectedLocation(next);
      setHasSearchInteraction(false);
      setSuggestionsOpen(false);
      setFetchedSuggestionsQuery('');
      setFetchedSuggestions([]);
    }
  };

  const applySuggestion = (suggestion: LocationSuggestion) => {
    skipSuggestionsRef.current = true;
    activeSearchControllerRef.current?.abort();
    const next: SavedLocation = { kind: 'city', city: suggestion.name };
    safeSetStorageItem(STORAGE_KEY, JSON.stringify(next));
    setDraftCity(suggestion.display_name);
    setSelectedLocation(next);
    setHasSearchInteraction(false);
    setFetchedSuggestionsQuery('');
    setFetchedSuggestions([]);
    setSuggestionsOpen(false);
  };

  const persistFavorites = (nextFavorites: SavedLocation[]) => {
    setFavoriteLocations(nextFavorites);
    safeSetStorageItem(FAVORITES_KEY, JSON.stringify(nextFavorites));
  };

  const toggleFavoriteLocation = () => {
    if (!selectedLocation) return;

    const exists = favoriteLocations.some((item) => isSameLocation(item, selectedLocation));
    if (exists) {
      persistFavorites(favoriteLocations.filter((item) => !isSameLocation(item, selectedLocation)));
      return;
    }

    const nextFavorites = [selectedLocation, ...favoriteLocations].slice(0, 5);
    persistFavorites(nextFavorites);
  };

  const selectFavoriteLocation = (location: SavedLocation) => {
    const normalized = normalizeSavedLocation(location);
    safeSetStorageItem(STORAGE_KEY, JSON.stringify(normalized));
    setSelectedLocation(normalized);
    setDraftCity(getLocationLabel(normalized));
    setHasSearchInteraction(false);
    setFetchedSuggestionsQuery('');
    setFetchedSuggestions([]);
    setSuggestionsOpen(false);
  };

  const useCurrentLocation = () => {
    if (!navigator.geolocation) {
      setError('Your browser does not support geolocation.');
      return;
    }

    setLocating(true);
    setError(null);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        skipSuggestionsRef.current = true;
        activeSearchControllerRef.current?.abort();
        const next: SavedLocation = {
          kind: 'coords',
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          label: 'Current Location',
        };
        safeSetStorageItem(STORAGE_KEY, JSON.stringify(next));
        setDraftCity('Current Location');
        setSelectedLocation(next);
        setLocating(false);
        setHasSearchInteraction(false);
        setFetchedSuggestionsQuery('');
        setFetchedSuggestions([]);
        setSuggestionsOpen(false);
      },
      () => {
        setError('Location permission was denied or the location could not be retrieved.');
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 },
    );
  };

  return (
    <div className="relative z-10 min-h-screen">
      <header className="max-w-7xl mx-auto px-5 md:px-8 pt-6 md:pt-8 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-xl bg-ink text-paper flex items-center justify-center">
            <CloudSun className="w-5 h-5" />
          </div>
          <div className="leading-tight">
            <div className="font-display text-lg tracking-tight">Bermuda-Bozok</div>
            <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">weather · ai</div>
          </div>
        </div>

        <form onSubmit={onSubmit} className="w-full lg:w-auto">
          <div className="flex gap-2 w-full lg:w-auto lg:min-w-[430px]">
            <div ref={searchBoxRef} className="relative min-w-0 w-full">
              <input
                value={draftCity}
                onChange={(event) => {
                  setHasSearchInteraction(true);
                  setDraftCity(event.target.value);
                  setSuggestionsOpen(true);
                }}
                placeholder="Search city"
                className="min-w-0 w-full rounded-2xl border border-line bg-[rgba(255,251,240,0.75)] px-4 py-3 outline-none focus:border-accent"
              />

              {hasSearchInteraction && suggestionsOpen && (activeSuggestions.length > 0 || searchingLocations || hasSearchAttempt) && (
                <div className="absolute left-0 right-0 top-[calc(100%+10px)] z-30 overflow-hidden rounded-2xl border border-line bg-[rgba(34,27,22,0.96)] text-paper shadow-[0_20px_50px_rgba(34,27,22,0.24)] backdrop-blur-md">
                  {searchingLocations && (
                    <div className="px-4 py-3 text-sm text-paper/70">Searching locations...</div>
                  )}

                  {!searchingLocations && activeSuggestions.map((suggestion) => (
                    <button
                      key={`${suggestion.name}-${suggestion.latitude}-${suggestion.longitude}`}
                      type="button"
                      onClick={() => applySuggestion(suggestion)}
                      className="flex w-full items-start justify-between gap-3 border-b border-white/8 px-4 py-3 text-left transition-colors hover:bg-white/8 last:border-b-0"
                    >
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium text-paper">{suggestion.name}</div>
                        <div className="truncate text-xs text-paper/60">
                          {[suggestion.admin1, suggestion.country].filter(Boolean).join(', ')}
                        </div>
                      </div>
                      <div className="shrink-0 text-[11px] text-paper/45">
                        {suggestion.latitude.toFixed(2)}, {suggestion.longitude.toFixed(2)}
                      </div>
                    </button>
                  ))}
                  {!searchingLocations && activeSuggestions.length === 0 && hasSearchAttempt && (
                    <div className="px-4 py-3 text-sm text-paper/70">No locations found.</div>
                  )}
                </div>
              )}
            </div>
            <button type="submit" className="rounded-2xl bg-ink text-paper px-4 py-3 flex items-center gap-2 shrink-0">
              <Search className="w-4 h-4" />
              Search
            </button>
            <button
              type="button"
              onClick={useCurrentLocation}
              className="rounded-2xl border border-line bg-[rgba(255,251,240,0.75)] px-4 py-3 flex items-center gap-2 shrink-0 text-ink-soft"
            >
              {locating ? <LoaderCircle className="w-4 h-4 animate-spin" /> : <MapPinned className="w-4 h-4" />}
              Location
            </button>
          </div>
        </form>
      </header>

      <main className="max-w-7xl mx-auto px-5 md:px-8 py-6 md:py-10">
        <div className="mb-5 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={toggleFavoriteLocation}
            disabled={!selectedLocation}
            className={`pill ${selectedLocation && favoriteLocations.some((item) => isSameLocation(item, selectedLocation)) ? 'active' : ''}`}
          >
            {selectedLocation && favoriteLocations.some((item) => isSameLocation(item, selectedLocation))
              ? 'Saved'
              : 'Save current'}
          </button>
          {favoriteLocations.map((location) => (
            <button
              key={getLocationStorageKey(location)}
              type="button"
              onClick={() => selectFavoriteLocation(location)}
              className={`pill ${selectedLocation && isSameLocation(location, selectedLocation) ? 'active' : ''}`}
            >
              {getLocationLabel(location)}
            </button>
          ))}
        </div>

        {loading && (
          <div className="card p-8 flex items-center gap-3 text-ink-soft mb-6">
            <LoaderCircle className="w-5 h-5 animate-spin" />
            Loading weather data...
          </div>
        )}

        {error && (
          <div className="card p-6 mb-6 border-accent/30">
            <div className="text-[11px] uppercase tracking-[0.18em] text-accent">Error</div>
            <p className="mt-2 text-ink">{error}</p>
          </div>
        )}

        {!loading && data && (
          <div className="space-y-5 md:space-y-7">
            {data.alert && <AlertBanner alert={data.alert} />}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 md:gap-7 items-start">
              <div className="flex min-w-0 flex-col gap-5 md:gap-6">
                <div className="card w-full min-w-0 overflow-hidden p-6 md:p-8">
                  <HeroTemperature location={data.location} liveData={data.live_data} />
                </div>
                <HourlyForecast entries={data.hourly_forecast} liveData={data.live_data} />
                <DailyForecast entries={data.daily_forecast} />
              </div>

              <div className="flex min-w-0 flex-col gap-5 md:gap-6">
                <AiCommentTop advice={data.ai_advice} />
                <OutfitPlanCard outfit={data.outfit_plan} />
                <ActivityPanel activitiesData={data.activities} activityWindows={data.activity_windows} />
                <WeatherHighlights liveData={data.live_data} />
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;

function normalizeSavedLocation(location: SavedLocation): SavedLocation {
  if (location.kind === 'city') {
    return location;
  }

  return {
    ...location,
    label: location.label && LEGACY_CURRENT_LOCATION_LABELS.has(location.label)
      ? 'Current Location'
      : location.label,
  };
}

function isSameLocation(left: SavedLocation, right: SavedLocation): boolean {
  if (left.kind !== right.kind) return false;
  if (left.kind === 'city' && right.kind === 'city') {
    return left.city.trim().toLowerCase() === right.city.trim().toLowerCase();
  }
  if (left.kind === 'coords' && right.kind === 'coords') {
    return left.latitude === right.latitude && left.longitude === right.longitude;
  }
  return false;
}

function getLocationLabel(location: SavedLocation): string {
  if (location.kind === 'city') return location.city;
  return location.label ?? `${location.latitude.toFixed(2)}, ${location.longitude.toFixed(2)}`;
}

function getLocationStorageKey(location: SavedLocation): string {
  if (location.kind === 'city') return `city:${location.city.toLowerCase()}`;
  return `coords:${location.latitude}:${location.longitude}`;
}

function readStoredLocation(): SavedLocation | null {
  const saved = safeGetStorageItem(STORAGE_KEY);
  if (!saved) return null;
  try {
    const parsed = parseSavedLocation(JSON.parse(saved));
    if (!parsed) {
      safeRemoveStorageItem(STORAGE_KEY);
      return null;
    }
    return normalizeSavedLocation(parsed);
  } catch {
    safeRemoveStorageItem(STORAGE_KEY);
    return null;
  }
}

function readStoredFavorites(): SavedLocation[] {
  const storedFavorites = safeGetStorageItem(FAVORITES_KEY);
  if (!storedFavorites) return [];
  try {
    const parsed = JSON.parse(storedFavorites);
    if (!Array.isArray(parsed)) {
      safeRemoveStorageItem(FAVORITES_KEY);
      return [];
    }
    return parsed
      .map(parseSavedLocation)
      .filter((location): location is SavedLocation => location !== null)
      .map(normalizeSavedLocation);
  } catch {
    safeRemoveStorageItem(FAVORITES_KEY);
    return [];
  }
}

function parseSavedLocation(value: unknown): SavedLocation | null {
  if (!isRecord(value) || typeof value.kind !== 'string') return null;

  if (value.kind === 'city') {
    if (typeof value.city !== 'string') return null;
    const city = value.city.trim();
    if (!city) return null;
    return { kind: 'city', city };
  }

  if (value.kind === 'coords') {
    if (!isFiniteNumber(value.latitude) || !isFiniteNumber(value.longitude)) return null;
    const label = typeof value.label === 'string' ? value.label : undefined;
    return {
      kind: 'coords',
      latitude: value.latitude,
      longitude: value.longitude,
      label,
    };
  }

  return null;
}

function safeGetStorageItem(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeSetStorageItem(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Storage can be unavailable in privacy-restricted browser contexts.
  }
}

function safeRemoveStorageItem(key: string): void {
  try {
    window.localStorage.removeItem(key);
  } catch {
    // Storage can be unavailable in privacy-restricted browser contexts.
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

export type RecommendationLevel = 'recommended' | 'acceptable' | 'not_recommended';
export type ConfidenceLevel = 'low' | 'medium' | 'high';

export type LiveWeatherData = {
  temperature_c: number;
  feels_like_c: number;
  precipitation_mm: number;
  wind_speed_kmh: number;
  wind_gust_kmh?: number | null;
  humidity_pct: number;
  wind_direction_deg?: number | null;
  cloud_cover_pct?: number | null;
  visibility_km?: number | null;
  uv_index?: number | null;
  european_aqi?: number | null;
  pm2_5_ugm3?: number | null;
  pm10_ugm3?: number | null;
  sunrise_local?: string | null;
  sunset_local?: string | null;
  weather_condition: string;
  season: string;
};

export type ActivityItem = {
  name: 'walking' | 'cycling' | 'outdoor_dining';
  recommendation: RecommendationLevel;
  reason: string;
};

export type OutfitPlan = {
  summary: string;
  layers: string[];
  accessories: string[];
  footwear: string;
};

export type WeatherAlert = {
  severity: 'info' | 'warning' | 'critical';
  title: string;
  message: string;
};

export type ActivityWindow = {
  activity: 'walking' | 'cycling' | 'outdoor_dining';
  best_time_window: string;
  summary: string;
  reason: string;
  confidence: ConfidenceLevel;
  score: number;
  recommendation: RecommendationLevel;
};

export type ForecastEntry = LiveWeatherData & {
  time_label: string;
};

export type DailyForecastItem = {
  date: string;
  label: string;
  weather_condition: string;
  temperature_high_c: number;
  temperature_low_c: number;
  precipitation_total_mm: number;
  precipitation_probability_max_pct?: number | null;
  uv_index_max?: number | null;
  sunshine_duration_hours?: number | null;
  wind_gust_max_kmh?: number | null;
  sunrise_local?: string | null;
  sunset_local?: string | null;
};

export type DashboardResponse = {
  status: string;
  location: string;
  headline: string;
  advice: string;
  reason: string;
  confidence: ConfidenceLevel;
  live_data: LiveWeatherData;
  ml_decision: {
    umbrella_needed: boolean;
    clothing_category: string;
  };
  outfit_plan: OutfitPlan;
  activity_advice: {
    activity: string;
    recommendation: RecommendationLevel;
    reason: string;
  };
  alert?: WeatherAlert | null;
  ai_advice: string;
  activities: ActivityItem[];
  activity_windows: ActivityWindow[];
  hourly_forecast: ForecastEntry[];
  daily_forecast: DailyForecastItem[];
};

export type SavedLocation =
  | { kind: 'city'; city: string }
  | { kind: 'coords'; latitude: number; longitude: number; label?: string };

export type LocationSuggestion = {
  name: string;
  country: string | null;
  admin1: string | null;
  admin2: string | null;
  latitude: number;
  longitude: number;
  display_name: string;
};

const API_BASE = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? '';

export async function fetchDashboard(location: SavedLocation): Promise<DashboardResponse> {
  const body =
  location.kind === 'city'
    ? {
        city: location.city.split(',')[0].trim(),
        activity: 'walking',
        language: 'en',
      }
    : {
        city: (location.label ?? `${location.latitude},${location.longitude}`).split(',')[0].trim(),
        activity: 'walking',
        language: 'en',
      };

  const response = await fetch(`${API_BASE}/weather/dashboard`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? 'Unable to load data.');
  }

  const payload = await response.json();
  return parseDashboardResponse(payload);
}

export async function fetchLocationSuggestions(
  query: string,
  signal?: AbortSignal,
): Promise<LocationSuggestion[]> {
  const response = await fetch(`${API_BASE}/cities/search?q=${encodeURIComponent(query)}`, { signal });

  if (!response.ok) {
    if (response.status === 422) return [];
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? 'Unable to load locations.');
  }

  const payload = await response.json();
  return parseLocationSuggestions(payload);
}

function parseDashboardResponse(payload: unknown): DashboardResponse {
  if (!isRecord(payload)) {
    throw new Error('Unexpected dashboard response.');
  }

  const requiredKeys = [
    'status',
    'location',
    'headline',
    'advice',
    'reason',
    'confidence',
    'live_data',
    'ml_decision',
    'outfit_plan',
    'activity_advice',
    'ai_advice',
    'activities',
    'activity_windows',
    'hourly_forecast',
    'daily_forecast',
  ] as const;

  for (const key of requiredKeys) {
    if (!(key in payload)) {
      throw new Error('Dashboard response is incomplete.');
    }
  }

  if (
    !Array.isArray(payload.activities) ||
    !Array.isArray(payload.activity_windows) ||
    !Array.isArray(payload.hourly_forecast) ||
    !Array.isArray(payload.daily_forecast)
  ) {
    throw new Error('Dashboard response is invalid.');
  }

  return payload as DashboardResponse;
}

function parseLocationSuggestions(payload: unknown): LocationSuggestion[] {
  if (!isRecord(payload) || !Array.isArray(payload.results)) {
    return [];
  }

  return payload.results
    .filter(isRecord)
    .map((item) => {
      const latitude = toFiniteNumber(item.latitude);
      const longitude = toFiniteNumber(item.longitude);
      const name = typeof item.name === 'string' ? item.name : '';
      if (latitude === null || longitude === null || !name) {
        return null;
      }
      return {
        name,
        country: typeof item.country === 'string' ? item.country : null,
        admin1: typeof item.admin1 === 'string' ? item.admin1 : null,
        admin2: typeof item.admin2 === 'string' ? item.admin2 : null,
        latitude,
        longitude,
        display_name:
          typeof item.display_name === 'string' && item.display_name.trim()
            ? item.display_name
            : name,
      };
    })
    .filter((item): item is LocationSuggestion => item !== null);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function toFiniteNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}
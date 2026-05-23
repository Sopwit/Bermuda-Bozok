import { useState } from "react";
import { MapPin } from "lucide-react";
import type { LiveWeatherData } from "../lib/api";
import { HeroWeatherArt } from "./HeroWeatherArt";

type HeroTemperatureProps = {
  location: string;
  liveData: LiveWeatherData;
};

export function HeroTemperature({ location, liveData }: HeroTemperatureProps) {
  const [unit, setUnit] = useState<"C" | "F">("C");
  const tempCValue = toFiniteNumber(liveData.temperature_c);
  const feelsLikeCValue = toFiniteNumber(liveData.feels_like_c);
  const windSpeedValue = toFiniteNumber(liveData.wind_speed_kmh);
  const humidityValue = toFiniteNumber(liveData.humidity_pct);

  const tempC = tempCValue !== null ? Math.round(tempCValue) : null;
  const tempF =
    tempCValue !== null ? Math.round((tempCValue * 9) / 5 + 32) : null;
  const feelsLikeDisplay =
    feelsLikeCValue === null
      ? "--"
      : unit === "C"
        ? `${Math.round(feelsLikeCValue)}°`
        : `${Math.round((feelsLikeCValue * 9) / 5 + 32)}°`;
  const value = unit === "C" ? tempC : tempF;
  const heroKind = getHeroWeatherKind(liveData.weather_condition);
  const conditionLabel = formatCondition(liveData.weather_condition);
  const windSummary =
    windSpeedValue === null
      ? "wind data unavailable"
      : windSpeedValue <= 12
        ? "light breeze"
        : "steady wind";
  const animatedHero = heroKind === "sun";

  return (
    <div className="relative w-full min-w-0">
      <div className="flex items-center gap-2 text-ink-muted text-sm mb-4">
        <MapPin className="w-4 h-4" />
        <span className="font-medium tracking-wide">{location}</span>
        <span className="text-ink-muted/60">· Now</span>
      </div>

      <div className="flex min-w-0 items-start gap-4 md:gap-6">
        <div className={`${animatedHero ? "float-slow" : ""} shrink-0`}>
          <HeroWeatherArt
            kind={heroKind}
            className="w-28 h-28 md:w-40 md:h-40"
          />
        </div>

        <div className="min-w-0 flex-1 pt-2">
          <div className="flex min-w-0 items-start">
            <span
              className="min-w-0 font-display font-light leading-none text-ink"
              style={{
                fontSize: "clamp(4.5rem, 12vw, 9rem)",
                letterSpacing: "-0.04em",
              }}
            >
              {value !== null ? `${value}°` : "--"}
            </span>

            <div className="ml-3 mt-3 md:mt-5 flex shrink-0 items-center gap-1 select-none">
              <button
                onClick={() => setUnit("C")}
                className={`font-display text-2xl md:text-3xl transition-colors ${unit === "C" ? "text-ink" : "text-ink-muted/50 hover:text-ink-soft"}`}
                aria-label="Celsius"
              >
                C
              </button>
              <span className="text-ink-muted/40 font-display text-2xl md:text-3xl">
                |
              </span>
              <button
                onClick={() => setUnit("F")}
                className={`font-display text-2xl md:text-3xl transition-colors ${unit === "F" ? "text-ink" : "text-ink-muted/50 hover:text-ink-soft"}`}
                aria-label="Fahrenheit"
              >
                F
              </button>
            </div>
          </div>

          <div className="mt-1 font-display italic text-ink-soft text-xl md:text-2xl">
            {conditionLabel} · {windSummary}
          </div>
          <div className="mt-1 text-sm text-ink-muted">
            Feels like {feelsLikeDisplay} · Humidity{" "}
            {humidityValue !== null ? `%${Math.round(humidityValue)}` : "--"} ·
            Wind{" "}
            {windSpeedValue !== null
              ? `${Math.round(windSpeedValue)} km/h`
              : "--"}
          </div>
        </div>
      </div>
    </div>
  );
}

function getHeroWeatherKind(condition: string | null | undefined) {
  const normalized = (condition ?? "").toLowerCase();
  const hour = new Date().getHours();
  const isNight = hour >= 20 || hour < 6;

  if (normalized.includes("thunder")) return "thunder";
  if (normalized.includes("snow")) return "snow";
  if (normalized.includes("rain") || normalized.includes("drizzle"))
    return "rain";
  if (
    normalized.includes("mist") ||
    normalized.includes("fog") ||
    normalized.includes("haze")
  )
    return "mist";
  if (normalized.includes("cloud")) return isNight ? "cloud" : "sun-cloud";
  if (normalized.includes("clear")) return isNight ? "moon" : "sun";
  return isNight ? "moon" : "sun";
}

function formatCondition(condition: string | null | undefined): string {
  const normalized = (condition ?? "").trim().toLowerCase();
  if (!normalized) return "unknown";
  return normalized;
}

function toFiniteNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

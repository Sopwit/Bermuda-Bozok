import {
  ArrowUp,
  Compass,
  Droplet,
  Droplets,
  Eye,
  ShieldAlert,
  Sunrise,
  Sunset,
  SunMedium,
  Wind,
} from "lucide-react";
import type { LiveWeatherData } from "../lib/api";

type WeatherHighlightsProps = {
  liveData: LiveWeatherData;
};

export function WeatherHighlights({ liveData }: WeatherHighlightsProps) {
  const windDirection = toCompassDirection(liveData.wind_direction_deg);
  const windFill = metricToPercent(liveData.wind_speed_kmh, 60);
  const uvFill =
    liveData.uv_index != null ? metricToPercent(liveData.uv_index, 11) : 0;
  const airFill =
    liveData.european_aqi != null
      ? metricToPercent(liveData.european_aqi, 100)
      : 0;

  return (
    <section className="card p-5 md:p-6">
      <header className="mb-4 border-b border-line pb-3">
        <h2 className="font-display text-xl md:text-2xl tracking-tight">
          <span className="ink-underline">Conditions</span>
        </h2>
      </header>

      <div className="space-y-3">
        <div className="rounded-2xl border border-line bg-[rgba(255,250,241,0.85)] p-4">
          <div className="flex items-center gap-2 text-sm text-ink-soft">
            <Sunrise className="w-4 h-4" />
            <span>Sun Cycle</span>
          </div>
          <div className="mt-4 grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] items-center gap-4">
            <SunMomentCard
              label="Sunrise"
              time={liveData.sunrise_local ?? "--:--"}
              align="left"
              art={<SunriseArt />}
            />

            <div className="hidden md:flex h-20 w-28 items-center justify-center">
              <div className="relative h-14 w-full overflow-hidden">
                <div className="absolute inset-x-0 bottom-1 h-10 rounded-t-full border-t-2 border-line-soft" />
                <div className="absolute left-1/2 top-1 -translate-x-1/2">
                  <div className="h-3.5 w-3.5 rounded-full bg-[#f8b74e] shadow-[0_0_18px_rgba(248,183,78,0.55)]" />
                </div>
              </div>
            </div>

            <SunMomentCard
              label="Sunset"
              time={liveData.sunset_local ?? "--:--"}
              align="right"
              art={<SunsetArt />}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 items-stretch gap-3">
          <div className="h-full rounded-2xl border border-line bg-[rgba(255,251,240,0.7)] p-4">
            <div className="flex items-center gap-2 text-sm text-ink-soft">
              <Wind className="w-4 h-4" />
              <span>Wind</span>
            </div>
            <div className="mt-4 flex items-center justify-between gap-4">
              <div className="shrink-0">
                <WindArt
                  direction={liveData.wind_direction_deg}
                  fill={windFill}
                />
              </div>
              <div className="flex-1 text-right">
                <div className="font-display text-3xl leading-none text-ink">
                  {Math.round(liveData.wind_speed_kmh)}{" "}
                  <span className="text-xl text-ink-soft">km/h</span>
                </div>
                <div className="mt-3 flex items-center justify-end gap-2 font-display text-2xl leading-none text-ink">
                  <span className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-line-soft bg-[rgba(255,255,255,0.72)]">
                    <Compass className="h-4 w-4 text-ink" strokeWidth={2.1} />
                  </span>
                  <span>{windDirection}</span>
                </div>
                <div className="mt-2 text-sm text-ink-muted">
                  {liveData.wind_gust_kmh != null
                    ? `Gusts up to ${Math.round(liveData.wind_gust_kmh)} km/h`
                    : liveData.wind_direction_deg != null
                      ? `${Math.round(liveData.wind_direction_deg)}° direction`
                      : "Direction unavailable"}
                </div>
              </div>
            </div>
          </div>

          <div className="h-full rounded-2xl border border-line bg-[rgba(249,246,239,0.92)] p-4">
            <div className="flex items-center gap-2 text-sm text-ink-soft">
              <Droplets className="w-4 h-4" />
              <span>Humidity</span>
            </div>
            <div className="mt-4 flex items-center justify-between gap-4">
              <div className="shrink-0">
                <HumidityArt value={liveData.humidity_pct} />
              </div>
              <div className="flex-1 text-right">
                <div className="font-display text-3xl leading-none text-ink">
                  {liveData.humidity_pct != null
                    ? `${liveData.humidity_pct}%`
                    : "--"}
                </div>
                <div className="mt-2 text-sm text-ink-muted">
                  {liveData.humidity_pct != null
                    ? describeHumidity(liveData.humidity_pct)
                    : "Humidity data unavailable"}
                </div>
              </div>
            </div>
          </div>

          <div className="h-full rounded-2xl border border-line bg-[rgba(255,251,240,0.7)] p-4">
            <div className="flex items-center gap-2 text-sm text-ink-soft">
              <SunMedium className="w-4 h-4" />
              <span>Exposure</span>
            </div>
            <div className="mt-4 flex items-center justify-between gap-4">
              <div className="shrink-0">
                <ExposureArt fill={uvFill} />
              </div>
              <div className="flex-1 text-right">
                <div className="font-display text-3xl leading-none text-ink">
                  {liveData.uv_index != null
                    ? Math.round(liveData.uv_index)
                    : "--"}
                </div>
                <div className="mt-2 text-sm text-ink-muted">
                  {liveData.uv_index != null
                    ? describeUv(liveData.uv_index)
                    : "UV data unavailable"}
                </div>
                <div className="mt-1 text-xs uppercase tracking-[0.14em] text-ink-muted">
                  {liveData.cloud_cover_pct != null
                    ? `Cloud cover ${liveData.cloud_cover_pct}%`
                    : "Exposure estimate"}
                </div>
              </div>
            </div>
          </div>

          <div className="h-full rounded-2xl border border-line bg-[rgba(249,246,239,0.92)] p-4">
            <div className="flex items-center gap-2 text-sm text-ink-soft">
              <ShieldAlert className="w-4 h-4" />
              <span>Air & Sight</span>
            </div>
            <div className="mt-4 flex items-center justify-between gap-4">
              <div className="shrink-0">
                <AirSightArt fill={airFill} />
              </div>
              <div className="flex-1 text-right">
                <div className="font-display text-3xl leading-none text-ink">
                  {liveData.european_aqi ?? "--"}
                </div>
                <div className="mt-2 text-sm text-ink-muted">
                  {liveData.european_aqi != null
                    ? `AQI ${aqiLabel(liveData.european_aqi)}`
                    : "Air quality unavailable"}
                </div>
                <div className="mt-1 text-xs uppercase tracking-[0.14em] text-ink-muted">
                  {liveData.visibility_km != null
                    ? `${liveData.visibility_km.toFixed(1)} km visibility`
                    : "Visibility unavailable"}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

type SunMomentCardProps = {
  label: string;
  time: string;
  art: React.ReactNode;
  align: "left" | "right";
};

function SunMomentCard({ label, time, art, align }: SunMomentCardProps) {
  return (
    <div
      className={`flex items-center gap-3 ${align === "right" ? "md:flex-row-reverse md:text-right" : ""}`}
    >
      <div className="shrink-0">{art}</div>
      <div>
        <div className="text-[11px] uppercase tracking-[0.16em] text-ink-muted">
          {label}
        </div>
        <div className="mt-1 font-display text-2xl text-ink">{time}</div>
      </div>
    </div>
  );
}

function SunriseArt() {
  return (
    <div className="relative flex h-16 w-16 items-center justify-center rounded-full border border-line-soft bg-[linear-gradient(180deg,rgba(255,250,241,0.95),rgba(247,238,222,0.95))]">
      <div className="absolute inset-x-3 bottom-4 h-4 rounded-t-full border-t border-line-soft" />
      <Sunrise className="h-7 w-7 text-[#db9440]" strokeWidth={1.8} />
    </div>
  );
}

function SunsetArt() {
  return (
    <div className="relative flex h-16 w-16 items-center justify-center rounded-full border border-line-soft bg-[linear-gradient(180deg,rgba(255,250,241,0.95),rgba(247,238,222,0.95))]">
      <div className="absolute inset-x-3 bottom-4 h-4 rounded-t-full border-t border-line-soft" />
      <Sunset className="h-7 w-7 text-[#d78448]" strokeWidth={1.8} />
    </div>
  );
}

function WindArt({
  direction,
  fill,
}: {
  direction?: number | null;
  fill: number;
}) {
  const rotation = direction ?? 0;

  return (
    <div className="relative flex h-16 w-16 items-center justify-center rounded-full border border-line-soft bg-[rgba(255,255,255,0.42)]">
      <div
        className="absolute inset-1 rounded-full"
        style={{
          background: `conic-gradient(#c88a48 ${fill * 3.6}deg, rgba(200,138,72,0.18) 0deg)`,
        }}
      />
      <div className="absolute inset-[6px] rounded-full bg-card/95" />
      <div className="absolute inset-2 rounded-full border border-line-soft/80" />
      <div
        className="absolute flex h-7 w-1 items-start justify-center origin-bottom"
        style={{ transform: `rotate(${rotation}deg)` }}
      >
        <ArrowUp className="h-4 w-4 -mt-1 text-[#c88a48]" strokeWidth={2.2} />
      </div>
      <Compass className="h-5 w-5 text-ink/75" strokeWidth={2.1} />
    </div>
  );
}

function HumidityArt({ value }: { value: number }) {
  const fill = Math.max(14, Math.min(88, value));

  return (
    <div className="relative flex h-16 w-16 items-center justify-center rounded-full border border-line-soft bg-[rgba(255,255,255,0.45)]">
      <div
        className="absolute inset-1 rounded-full"
        style={{
          background: `conic-gradient(#79aee0 ${fill * 3.6}deg, rgba(121,174,224,0.18) 0deg)`,
        }}
      />
      <div className="absolute inset-[6px] rounded-full bg-card/95" />
      <Droplet className="relative h-6 w-6 text-[#79aee0]" strokeWidth={1.9} />
    </div>
  );
}

function ExposureArt({ fill }: { fill: number }) {
  return (
    <div className="relative flex h-16 w-16 items-center justify-center rounded-full border border-line-soft bg-[rgba(255,255,255,0.42)]">
      <div
        className="absolute inset-1 rounded-full"
        style={{
          background: `conic-gradient(#d78f32 ${fill * 3.6}deg, rgba(215,143,50,0.18) 0deg)`,
        }}
      />
      <div className="absolute inset-[6px] rounded-full bg-card/95" />
      <SunMedium
        className="relative h-6 w-6 text-[#d78f32]"
        strokeWidth={1.9}
      />
    </div>
  );
}

function AirSightArt({ fill }: { fill: number }) {
  return (
    <div className="relative flex h-16 w-16 items-center justify-center rounded-full border border-line-soft bg-[rgba(255,255,255,0.42)]">
      <div
        className="absolute inset-1 rounded-full"
        style={{
          background: `conic-gradient(#7e8fa5 ${fill * 3.6}deg, rgba(126,143,165,0.18) 0deg)`,
        }}
      />
      <div className="absolute inset-[6px] rounded-full bg-card/95" />
      <Eye className="relative h-6 w-6 text-[#7e8fa5]" strokeWidth={1.9} />
    </div>
  );
}

function metricToPercent(value: number, max: number): number {
  if (!Number.isFinite(value) || max <= 0) return 0;
  return Math.max(0, Math.min(100, (value / max) * 100));
}

function toCompassDirection(value?: number | null): string {
  if (value == null) return "Unknown";

  const directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
  const index = ((Math.round(value / 45) % 8) + 8) % 8;
  return directions[index];
}

function describeHumidity(value: number): string {
  if (value >= 80) return "High moisture in the air";
  if (value >= 55) return "Balanced indoor-outdoor feel";
  if (value >= 35) return "Comfortably dry conditions";
  return "Dry air is dominant";
}

function describeUv(value: number): string {
  if (value >= 8) return "High UV exposure outdoors";
  if (value >= 6) return "Strong sun on open surfaces";
  if (value >= 3) return "Moderate daytime exposure";
  return "Low direct sun risk";
}

function aqiLabel(aqi: number): string {
  if (aqi <= 20) return "good";
  if (aqi <= 40) return "fair";
  if (aqi <= 60) return "moderate";
  if (aqi <= 80) return "poor";
  if (aqi <= 100) return "very poor";
  return "extreme";
}

import { WeatherIcon, type WeatherKind } from './WeatherIcon';
import { Droplets } from 'lucide-react';
import type { DailyForecastItem } from '../lib/api';
import { formatDayLabel, toWeatherKind } from '../lib/weather';

type Day = {
  label: string;
  pop: number;
  day: WeatherKind;
  night: WeatherKind;
  hi: number;
  lo: number;
};

type DailyForecastProps = {
  entries: DailyForecastItem[];
};

export function DailyForecast({ entries }: DailyForecastProps) {
  const days: Day[] = entries.map((entry) => {
    const kind = toWeatherKind(entry.weather_condition);
    return {
      label: formatDayLabel(entry.date),
      pop: entry.precipitation_probability_max_pct ?? clampWeatherPercent(entry.precipitation_total_mm),
      day: kind,
      night: toNightKind(kind),
      hi: Math.round(entry.temperature_high_c),
      lo: Math.round(entry.temperature_low_c),
    };
  });

  return (
    <section className="card w-full p-5 md:p-6">
      <header className="flex items-baseline justify-between border-b border-line pb-3 mb-2">
        <h2 className="font-display text-xl md:text-2xl tracking-tight">
          <span className="ink-underline">Daily Outlook</span>
        </h2>
      </header>

      <ul className="divide-y divide-line-soft">
        {days.map((d) => (
          <li key={d.label} className="grid grid-cols-12 items-center gap-2 py-3">
            <div className="col-span-3 md:col-span-2 font-medium text-ink">{d.label}</div>

            <div className="col-span-3 md:col-span-2 flex items-center gap-1 text-[11px] text-rain">
              <Droplets className="w-3 h-3" />
              <span>%{d.pop}</span>
            </div>

            <div className="col-span-3 md:col-span-5 flex items-center justify-center text-ink-muted">
              <div className="flex items-center justify-center gap-4 rounded-2xl bg-paper-2/35 px-4 py-2 min-w-[122px]">
                <div className="flex items-center justify-center w-8">
                  <WeatherIcon kind={d.day} className="w-7 h-7" />
                </div>
                <div className="flex items-center justify-center w-8">
                  <WeatherIcon kind={d.night} className="w-7 h-7" />
                </div>
              </div>
            </div>

            <div className="col-span-3 md:col-span-3 flex items-center justify-end gap-5">
              <div className="text-right min-w-[36px]">
                <div className="font-display text-xl text-ink-muted tabular-nums">{d.lo}°</div>
              </div>
              <div className="text-right min-w-[36px]">
                <div className="font-display text-xl text-ink tabular-nums">{d.hi}°</div>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function toNightKind(kind: WeatherKind): WeatherKind {
  if (kind === 'sun' || kind === 'partly' || kind === 'sun-cloud') {
    return 'moon';
  }
  return kind;
}

function clampWeatherPercent(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value * 10)));
}

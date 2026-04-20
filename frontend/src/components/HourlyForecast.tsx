import { useMemo, useRef } from 'react';
import { WeatherIcon, type WeatherKind } from './WeatherIcon';
import { Droplets, ChevronLeft, ChevronRight } from 'lucide-react';
import type { ForecastEntry, LiveWeatherData } from '../lib/api';
import { toWeatherKind } from '../lib/weather';

type Hour = {
  time: string;
  kind: WeatherKind;
  temp: number;
  pop: number;
};

type HourlyForecastProps = {
  entries: ForecastEntry[];
  liveData: LiveWeatherData;
};

export function HourlyForecast({ entries, liveData }: HourlyForecastProps) {
  const scrollerRef = useRef<HTMLDivElement>(null);

  const hours = useMemo<Hour[]>(() => {
    const currentHourCard: Hour = {
      time: 'Now',
      kind: toWeatherKind(liveData.weather_condition, new Date().toISOString()),
      temp: Math.round(liveData.temperature_c),
      pop: clampWeatherPercent(liveData.precipitation_mm),
    };

    const futureHours: Hour[] = entries
      .filter((entry) => entry.time_label && entry.time_label.trim() !== '')
      .map((entry) => ({
        time: entry.time_label,
        kind: toWeatherKind(entry.weather_condition, new Date().toISOString()),
        temp: Math.round(entry.temperature_c),
        pop: clampWeatherPercent(entry.precipitation_mm),
      }));

    const seen = new Set<string>();
    const merged = [currentHourCard, ...futureHours].filter((item) => {
      if (seen.has(item.time)) return false;
      seen.add(item.time);
      return true;
    });

    console.log('HOURS AFTER BUILD:', merged);
    console.log('HOURS AFTER BUILD LENGTH:', merged.length);

    return merged.slice(0, 24);
  }, [entries, liveData]);

  const max = hours.length ? Math.max(...hours.map((h) => h.temp)) : Math.round(liveData.temperature_c);
  const low = hours.length ? Math.min(...hours.map((h) => h.temp)) : Math.round(liveData.temperature_c);

  const scrollBy = (dir: 1 | -1) => {
    const el = scrollerRef.current;
    if (!el) return;
    el.scrollBy({ left: dir * 420, behavior: 'smooth' });
  };

  return (
    <section className="card w-full p-5 md:p-6 self-start">
      <header className="flex items-baseline justify-between border-b border-line pb-3 mb-4">
        <h2 className="font-display text-xl md:text-2xl tracking-tight">
          <span className="ink-underline">Hourly Weather</span>
        </h2>
        <div className="flex items-center gap-4 text-xs font-medium text-ink-muted">
          <div className="flex items-baseline gap-1">
            <span className="uppercase tracking-wider text-[10px]">max</span>
            <span className="text-ink font-display text-base">{max}°</span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="uppercase tracking-wider text-[10px]">min</span>
            <span className="text-ink font-display text-base">{low}°</span>
          </div>
        </div>
      </header>

      <div className="relative">
        <button
          onClick={() => scrollBy(-1)}
          aria-label="Scroll back"
          className="hidden md:flex absolute -left-10 top-1/2 -translate-y-1/2 z-10 w-8 h-8 items-center justify-center rounded-full bg-card border border-line shadow-sm hover:bg-paper-2 hover:border-accent/40 transition-colors"
        >
          <ChevronLeft className="w-4 h-4 text-ink-soft" />
        </button>

        <button
          onClick={() => scrollBy(1)}
          aria-label="Scroll forward"
          className="hidden md:flex absolute -right-4 top-1/2 -translate-y-1/2 z-10 w-8 h-8 items-center justify-center rounded-full bg-card border border-line shadow-sm hover:bg-paper-2 hover:border-accent/40 transition-colors"
        >
          <ChevronRight className="w-4 h-4 text-ink-soft" />
        </button>

        <div
          ref={scrollerRef}
          className="overflow-x-auto scroll-smooth px-2"
        >
          <div className="flex gap-3 py-2 min-w-max">
            {hours.map((h, i) => {
              const isNow = i === 0;
              return (
                <div
                  key={`${h.time}-${i}`}
                  className={`flex flex-col items-center justify-center rounded-2xl border shrink-0 px-4 py-4 w-[92px] min-w-[92px] ${
                    isNow
                      ? 'bg-accent/10 border-accent/30'
                      : 'bg-transparent border-line'
                  }`}
                >
                  <div className={`text-sm font-medium ${isNow ? 'text-accent' : 'text-ink-soft'}`}>
                    {h.time}
                  </div>
                  <WeatherIcon kind={h.kind} className="w-10 h-10 my-3" />
                  <div className="font-display text-2xl leading-none text-ink">{h.temp}°</div>
                  <div className="mt-2 flex items-center gap-1 text-[11px] text-rain">
                    <Droplets className="w-3 h-3" />
                    <span>%{h.pop}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}

function clampWeatherPercent(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value * 10)));
}
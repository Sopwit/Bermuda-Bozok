import type { ReactNode } from 'react';
import { Footprints, Layers3, Sparkles, Umbrella } from 'lucide-react';
import type { OutfitPlan } from '../lib/api';

type OutfitPlanCardProps = {
  outfit: OutfitPlan;
};

export function OutfitPlanCard({ outfit }: OutfitPlanCardProps) {
  const normalizedSummary = formatSummary(outfit.summary);
  const layerItems = normalizeList(outfit.layers);
  const accessoryItems = normalizeList(outfit.accessories);
  const footwearItems = normalizeList([outfit.footwear]);

  return (
    <section className="card px-5 py-4 md:px-6 md:py-5">
      <header className="mb-3 flex items-center gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-full border border-accent/30 bg-accent/10">
          <Sparkles className="h-4 w-4 text-accent" />
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-ink-muted font-semibold">
            Outfit Plan
          </div>
          <p className="font-display italic text-ink text-lg leading-snug">{normalizedSummary}</p>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 items-stretch gap-2.5 md:gap-3">
        <InfoCard
          icon={<Layers3 className="w-4 h-4" />}
          title="Layers"
          items={layerItems}
          fallback="Add a light layer"
        />
        <InfoCard
          icon={<Umbrella className="w-4 h-4" />}
          title="Accessories"
          items={accessoryItems}
          fallback="No extras needed"
        />
        <InfoCard
          icon={<Footprints className="w-4 h-4" />}
          title="Footwear"
          items={footwearItems}
          fallback="Regular sneakers"
        />
      </div>
    </section>
  );
}

type InfoCardProps = {
  icon: ReactNode;
  title: string;
  items: string[];
  fallback: string;
};

function InfoCard({ icon, title, items, fallback }: InfoCardProps) {
  const displayItems = items.length > 0 ? items : [fallback];

  return (
    <div className="h-full rounded-2xl border border-line bg-card p-3.5 md:p-4">
      <div className="flex min-h-[22px] items-center gap-2 text-ink-soft text-sm">
        {icon}
        <span>{title}</span>
      </div>

      <ul className="mt-2.5 space-y-1.5">
        {displayItems.map((item, index) => (
          <li
            key={`${title}-${item}-${index}`}
            className="text-sm font-semibold text-ink leading-snug"
          >
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

function normalizeList(values: string[]): string[] {
  const normalized = values
    .map((value) => value.trim().replace(/\s+/g, ' '))
    .filter(Boolean)
    .map(cleanPhrase);

  return Array.from(new Set(normalized.map((item) => item.toLowerCase())))
    .map((key) => normalized.find((item) => item.toLowerCase() === key) as string);
}

function formatSummary(summary: string): string {
  const trimmed = summary.trim().replace(/\s+/g, ' ');
  if (!trimmed) return 'Plan your outfit based on today\'s weather.';

  const noTrailingPunctuation = trimmed.replace(/[\s:;,.-]+$/g, '');
  const sentence = noTrailingPunctuation.charAt(0).toUpperCase() + noTrailingPunctuation.slice(1);
  return /[.!?]$/.test(sentence) ? sentence : `${sentence}.`;
}

function cleanPhrase(value: string): string {
  const normalized = value
    .replace(/_/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  if (!normalized) return normalized;
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

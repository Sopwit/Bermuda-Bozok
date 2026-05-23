import { useState } from 'react';
import {
  Sparkles,
  Footprints,
  Bike,
  TreePine,
  type LucideIcon,
} from 'lucide-react';
import type { ActivityItem, ActivityWindow } from '../lib/api';
import { humanizeActivity } from '../lib/weather';

type ActivityKey = 'walking' | 'cycling' | 'outdoor_dining';

type Activity = {
  key: ActivityKey;
  label: string;
  icon: LucideIcon;
};

const activities: Activity[] = [
  { key: 'walking', label: 'Walking', icon: Footprints },
  { key: 'cycling', label: 'Cycling', icon: Bike },
  { key: 'outdoor_dining', label: 'Outdoor', icon: TreePine },
];

type ActivityPanelProps = {
  activitiesData: ActivityItem[];
  activityWindows: ActivityWindow[];
};

export function ActivityPanel({ activitiesData, activityWindows }: ActivityPanelProps) {
  const [active, setActive] = useState<ActivityKey>('walking');
  const activity = activities.find((item) => item.key === active) ?? activities[0];
  const activitySummary = activitiesData.find((item) => item.name === active);
  const bestWindow = activityWindows.find((item) => item.activity === active);

  const suitabilityScore = bestWindow?.score ?? 0;

  if (!activitySummary || !bestWindow) return null;

  const scoreText = buildScoreText(
    bestWindow.recommendation,
    suitabilityScore,
    active,
  );

  const windowLabel = buildWindowLabel(
    bestWindow.recommendation,
    suitabilityScore,
  );

  const noteText = buildActivityNote({
    activity: active,
    recommendation: bestWindow.recommendation,
    bestTimeWindow: bestWindow.best_time_window,
    reason: bestWindow.reason,
    score: suitabilityScore,
  });

  return (
    <section className="card p-4 sm:p-5 md:p-6">
      <header className="flex items-center justify-between flex-wrap gap-3 mb-4">
        <h2 className="font-display text-[1.45rem] md:text-2xl tracking-tight">
          <span className="ink-underline">Activity Suggestions</span>
        </h2>
        <div className="flex items-center gap-2 flex-wrap">
          {activities.map((item) => {
            const Icon = item.icon;
            const isActive = active === item.key;
            return (
              <button
                key={item.key}
                onClick={() => setActive(item.key)}
                className={`pill flex items-center gap-1.5 ${isActive ? 'active' : ''}`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span className="font-medium">{item.label}</span>
              </button>
            );
          })}
        </div>
      </header>

      <div className="grid grid-cols-1 gap-4 rounded-[20px] border border-line bg-paper-2/50 px-4 py-3.5 mb-4 md:grid-cols-[minmax(0,1.15fr)_minmax(0,0.95fr)]">
        <div className="flex items-center gap-3 min-w-0">
          <div className="shrink-0 w-10 h-10 rounded-xl bg-ink text-paper flex items-center justify-center">
            <activity.icon className="w-5 h-5" />
          </div>
          <div className="min-w-0">
            <div className="text-[10px] uppercase tracking-[0.2em] text-ink-muted">
              {windowLabel}
            </div>
            <div className="font-display text-[1.55rem] md:text-[1.75rem] text-ink leading-none whitespace-nowrap">
              {bestWindow.best_time_window}
            </div>
          </div>
        </div>

        <div className="w-full min-w-0 md:max-w-[360px] md:ml-auto md:text-right">
          <div className="text-[10px] uppercase tracking-[0.2em] text-ink-muted">
            Activity Score
          </div>
          <div className="mt-1 grid gap-1 md:justify-items-end">
            <div className="font-display text-[1.9rem] md:text-[2rem] text-ink leading-none">
              {suitabilityScore}/100
            </div>
            <div className="max-w-[16ch] text-[10px] uppercase tracking-[0.14em] text-ink-muted leading-tight">
              {scoreText}
            </div>
          </div>
          <div className="mt-2 h-1 w-full max-w-[320px] overflow-hidden rounded-full bg-line-soft md:ml-auto">
            <div
              className="h-full rounded-full bg-ink"
              style={{ width: `${suitabilityScore}%` }}
            />
          </div>
        </div>
      </div>

      <div className="divider-ink my-4" />

      <div className="flex items-start gap-3">
        <div className="shrink-0 w-7 h-7 rounded-full bg-accent/10 border border-accent/30 flex items-center justify-center">
          <Sparkles className="w-3.5 h-3.5 text-accent" />
        </div>
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-[0.2em] text-ink-muted font-semibold">
            AI Note
          </div>
          <p className="font-display italic text-ink text-[1.05rem] md:text-[1.2rem] leading-[1.55] mt-0.5 max-w-[62ch]">
            {noteText}
          </p>
        </div>
      </div>
    </section>
  );
}


function buildWindowLabel(
  recommendation: ActivityItem['recommendation'],
  score: number,
): string {
  if (recommendation === 'not_recommended' || score < 45) {
    return 'Least risky window';
  }
  if (recommendation === 'acceptable' || score < 70) {
    return 'Better window';
  }
  return 'Best window';
}

function buildScoreText(
  recommendation: ActivityItem['recommendation'],
  score: number,
  activity: ActivityKey,
): string {
  const activityLabel = humanizeActivity(activity).toLowerCase();

  if (recommendation === 'not_recommended' || score < 45) {
    return `Not ideal for ${activityLabel}`;
  }
  if (recommendation === 'acceptable' || score < 70) {
    return `Fair for ${activityLabel}`;
  }
  if (score >= 85) {
    return `Great for ${activityLabel}`;
  }
  return `Good for ${activityLabel}`;
}

function buildActivityNote(args: {
  activity: ActivityKey;
  recommendation: ActivityItem['recommendation'];
  bestTimeWindow: string;
  reason: string;
  score: number;
}): string {
  const activityName = humanizeActivity(args.activity);
  const readableReason = toEnglishReason(args.reason, args.activity);
  const cleanReason = ensureSentence(readableReason);

  if (args.recommendation === 'not_recommended' || args.score < 45) {
    return `${activityName} is not a strong option today. If you still want to go ahead, ${args.bestTimeWindow} looks like the least risky window.`;
  }

  if (args.recommendation === 'acceptable' || args.score < 70) {
    return `${activityName} is possible, but conditions are only moderately favorable. ${args.bestTimeWindow} looks like the better window. ${cleanReason}`;
  }

  return `${activityName} looks strongest around ${args.bestTimeWindow}. ${cleanReason}`;
}

function ensureSentence(text: string): string {
  const cleaned = text.replace(/\s+/g, ' ').trim();
  if (!cleaned) return '';
  return cleaned.endsWith('.') ? cleaned : `${cleaned}.`;
}

function toEnglishReason(reason: string, activity: ActivityKey): string {
  const normalized = reason.trim().toLowerCase();

  if (normalized.includes('least risky')) {
    return 'This window is safer than the nearby hours, but conditions are still not ideal.';
  }
  if (normalized.includes('moderately suitable')) {
    return 'Conditions are manageable here, but not strong enough to feel ideal.';
  }
  if (normalized.includes('dry weather')) {
    return `Low rain risk and steady conditions make ${humanizeActivity(activity).toLowerCase()} feel suitable.`;
  }
  if (normalized.includes('comfortable wind')) {
    return 'Wind levels are balanced, so staying outside should feel more comfortable.';
  }
  if (normalized.includes('temperature is cold')) {
    return 'The temperature is on the cold side, so layered clothing is the safer choice.';
  }
  if (normalized.includes('wind is light')) {
    return 'Wind is light and the overall feel is calm.';
  }
  if (normalized.includes('temperature is comfortable')) {
    return 'The temperature looks comfortable for being outside.';
  }
  if (normalized.includes('risky')) {
    return `${humanizeActivity(activity)} becomes riskier under the current conditions.`;
  }
  if (normalized.includes('rain')) {
    return 'Rain risk reduces overall comfort and reliability.';
  }

  return replaceCommonEnglish(reason);
}

function replaceCommonEnglish(text: string): string {
  return text
    .replace(/dry weather/gi, 'dry weather')
    .replace(/comfortable wind/gi, 'comfortable wind')
    .replace(/temperature is cold/gi, 'temperature is cold')
    .replace(/temperature is comfortable/gi, 'temperature is comfortable')
    .replace(/wind is light/gi, 'wind is light')
    .replace(/suitable/gi, 'suitable')
    .replace(/fine/gi, 'fine')
    .replace(/\s+/g, ' ')
    .trim();
}

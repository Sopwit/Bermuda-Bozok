import { AlertTriangle, Info, ShieldAlert } from 'lucide-react';
import type { WeatherAlert } from '../lib/api';

type AlertBannerProps = {
  alert: WeatherAlert;
};

export function AlertBanner({ alert }: AlertBannerProps) {
  const meta = getAlertMeta(alert.severity);
  const Icon = meta.icon;

  return (
    <section className={`rounded-2xl border px-5 py-4 ${meta.className}`}>
      <div className="flex items-start gap-3">
        <div className="mt-0.5 shrink-0">
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <div className="text-[11px] uppercase tracking-[0.18em] font-semibold opacity-75">
            {meta.eyebrow}
          </div>
          <div className="mt-1 font-display text-xl text-ink">{alert.title}</div>
          <p className="mt-1 text-sm text-ink-soft">{alert.message}</p>
        </div>
      </div>
    </section>
  );
}

function getAlertMeta(severity: WeatherAlert['severity']) {
  if (severity === 'critical') {
    return {
      eyebrow: 'Critical',
      icon: ShieldAlert,
      className: 'border-accent/35 bg-[rgba(179,58,46,0.08)] text-accent',
    };
  }
  if (severity === 'warning') {
    return {
      eyebrow: 'Attention',
      icon: AlertTriangle,
      className: 'border-[#d7a14b]/35 bg-[rgba(215,161,75,0.1)] text-[#9d6627]',
    };
  }
  return {
    eyebrow: 'Heads up',
    icon: Info,
    className: 'border-line bg-[rgba(255,251,240,0.75)] text-ink-soft',
  };
}

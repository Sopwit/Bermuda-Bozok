export type WeatherKind =
  | "sun"
  | "partly"
  | "cloud"
  | "rain"
  | "sun-cloud"
  | "moon"
  | "thunder";

export function toWeatherKind(
  condition: string,
  timeLabel?: string,
): WeatherKind {
  const normalized = condition.toLowerCase();
  const isNight = getIsNight(timeLabel);

  if (normalized.includes("thunder")) return "thunder";
  if (normalized.includes("rain") || normalized.includes("drizzle"))
    return "rain";
  if (normalized.includes("cloud")) return isNight ? "cloud" : "sun-cloud";
  if (normalized.includes("clear")) return isNight ? "moon" : "sun";
  if (
    normalized.includes("mist") ||
    normalized.includes("fog") ||
    normalized.includes("haze")
  )
    return "cloud";
  return isNight ? "moon" : "partly";
}

export function formatHour(timeLabel: string): string {
  const parsed = new Date(timeLabel);
  return Number.isNaN(parsed.getTime())
    ? timeLabel.slice(11, 16)
    : parsed.toLocaleTimeString("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
      });
}

export function formatDayLabel(date: string): string {
  const parsed = new Date(date);
  if (Number.isNaN(parsed.getTime())) return date;

  const today = new Date();
  if (parsed.toDateString() === today.toDateString()) return "Today";
  return parsed.toLocaleDateString("en-US", { weekday: "short" });
}

export function humanizeActivity(activity: string): string {
  const labels: Record<string, string> = {
    walking: "Walking",
    cycling: "Cycling",
    outdoor_dining: "Outdoor",
  };
  return labels[activity] ?? activity;
}

export function humanizeRecommendation(recommendation: string): string {
  const labels: Record<string, string> = {
    recommended: "Recommended",
    acceptable: "Acceptable",
    not_recommended: "Not Recommended",
  };
  return labels[recommendation] ?? recommendation;
}

export function humanizeWeatherCondition(condition: string): string {
  const labels: Record<string, string> = {
    clear: "Clear",
    clouds: "Cloudy",
    drizzle: "Drizzle",
    rain: "Rainy",
    snow: "Snow",
    thunderstorm: "Storm",
  };
  return labels[condition] ?? condition;
}

function getIsNight(timeLabel?: string): boolean {
  if (!timeLabel) {
    const currentHour = new Date().getHours();
    return currentHour >= 20 || currentHour < 6;
  }

  const parsed = new Date(timeLabel);
  if (Number.isNaN(parsed.getTime())) {
    const hour = Number(timeLabel.slice(11, 13));
    return hour >= 20 || hour < 6;
  }

  const hour = parsed.getHours();
  return hour >= 20 || hour < 6;
}

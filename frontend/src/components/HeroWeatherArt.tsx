type HeroWeatherKind =
  | "sun"
  | "moon"
  | "sun-cloud"
  | "cloud"
  | "rain"
  | "thunder"
  | "snow"
  | "mist";

export function HeroWeatherArt({
  kind,
  className = "",
}: {
  kind: HeroWeatherKind;
  className?: string;
}) {
  switch (kind) {
    case "sun":
      return <SunArt className={className} />;
    case "moon":
      return <MoonArt className={className} />;
    case "sun-cloud":
      return <SunCloudArt className={className} />;
    case "cloud":
      return <CloudArt className={className} />;
    case "rain":
      return <RainArt className={className} />;
    case "thunder":
      return <ThunderArt className={className} />;
    case "snow":
      return <SnowArt className={className} />;
    case "mist":
      return <MistArt className={className} />;
  }
}

function SunArt({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 200 200" className={className} aria-hidden>
      <defs>
        <radialGradient id="sunCoreHero" cx="50%" cy="45%" r="55%">
          <stop offset="0%" stopColor="#FFD98A" />
          <stop offset="60%" stopColor="#F4B04A" />
          <stop offset="100%" stopColor="#E8872C" />
        </radialGradient>
        <filter id="glowHeroSun" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="6" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <g className="spin-slow">
        <g stroke="#B33A2E" strokeWidth="3" strokeLinecap="round" fill="none">
          <line x1="100" y1="18" x2="100" y2="40" />
          <line x1="100" y1="160" x2="100" y2="182" />
          <line x1="18" y1="100" x2="40" y2="100" />
          <line x1="160" y1="100" x2="182" y2="100" />
          <line x1="38" y1="38" x2="54" y2="54" />
          <line x1="146" y1="146" x2="162" y2="162" />
          <line x1="38" y1="162" x2="54" y2="146" />
          <line x1="146" y1="54" x2="162" y2="38" />
        </g>
      </g>
      <g filter="url(#glowHeroSun)">
        <circle cx="100" cy="100" r="44" fill="url(#sunCoreHero)" />
      </g>
      <circle
        cx="100"
        cy="100"
        r="46"
        fill="none"
        stroke="#B33A2E"
        strokeWidth="2.5"
      />
    </svg>
  );
}

function MoonArt({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 200 200" className={className} aria-hidden>
      <defs>
        <filter id="glowHeroMoon" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="5" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <g filter="url(#glowHeroMoon)">
        <path
          d="M120 32c-10 0-19 2-28 6a78 78 0 1 0 87 88c-11 28-38 48-71 48-43 0-78-35-78-78 0-30 17-56 42-69 12-6 30-10 48-8z"
          fill="#F4C26B"
          stroke="#5A4635"
          strokeWidth="4"
          strokeLinejoin="round"
        />
      </g>
      <circle cx="140" cy="52" r="4" fill="#B33A2E" opacity="0.8" />
      <circle cx="158" cy="66" r="2.5" fill="#B33A2E" opacity="0.7" />
    </svg>
  );
}

function CloudArt({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 200 200" className={className} aria-hidden>
      <g fill="#F1E6D0" stroke="#8A7760" strokeWidth="4" strokeLinejoin="round">
        <path d="M53 122c0-16 13-29 29-29 4-14 17-24 33-24 20 0 37 15 39 35h3c16 0 29 13 29 29s-13 29-29 29H67c-19 0-34-15-34-34 0-7 2-12 8-16z" />
      </g>
    </svg>
  );
}

function SunCloudArt({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 200 200" className={className} aria-hidden>
      <g transform="translate(92 28)">
        <circle
          cx="28"
          cy="28"
          r="18"
          fill="#F4C26B"
          stroke="#E8A43A"
          strokeWidth="3"
        />
        <g stroke="#E8A43A" strokeWidth="3" strokeLinecap="round">
          <line x1="28" y1="0" x2="28" y2="10" />
          <line x1="28" y1="46" x2="28" y2="56" />
          <line x1="0" y1="28" x2="10" y2="28" />
          <line x1="46" y1="28" x2="56" y2="28" />
          <line x1="8" y1="8" x2="14" y2="14" />
          <line x1="42" y1="42" x2="48" y2="48" />
          <line x1="8" y1="48" x2="14" y2="42" />
          <line x1="42" y1="14" x2="48" y2="8" />
        </g>
      </g>
      <g fill="#F1E6D0" stroke="#8A7760" strokeWidth="4" strokeLinejoin="round">
        <path d="M44 124c0-15 12-27 27-27 4-13 16-22 31-22 19 0 35 14 38 32h3c15 0 27 12 27 27s-12 27-27 27H57c-17 0-31-14-31-31 0-5 2-10 6-13z" />
      </g>
    </svg>
  );
}

function RainArt({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 200 200" className={className} aria-hidden>
      <g fill="#D8E4EC" stroke="#6E98BB" strokeWidth="4" strokeLinejoin="round">
        <path d="M46 112c0-15 12-27 27-27 4-13 16-22 31-22 19 0 35 14 38 32h3c15 0 27 12 27 27s-12 27-27 27H59c-17 0-31-14-31-31 0-5 2-10 6-13z" />
      </g>
      <g stroke="#4A7FA3" strokeWidth="4" strokeLinecap="round">
        <line x1="68" y1="154" x2="62" y2="170" />
        <line x1="100" y1="156" x2="94" y2="172" />
        <line x1="132" y1="154" x2="126" y2="170" />
      </g>
    </svg>
  );
}

function ThunderArt({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 200 200" className={className} aria-hidden>
      <g fill="#D8E4EC" stroke="#6E98BB" strokeWidth="4" strokeLinejoin="round">
        <path d="M46 112c0-15 12-27 27-27 4-13 16-22 31-22 19 0 35 14 38 32h3c15 0 27 12 27 27s-12 27-27 27H59c-17 0-31-14-31-31 0-5 2-10 6-13z" />
      </g>
      <path
        d="M103 138l-18 26h18l-10 26 34-40h-19l10-22z"
        fill="#F0B13C"
        stroke="#B07520"
        strokeWidth="3"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function SnowArt({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 200 200" className={className} aria-hidden>
      <g fill="#E7F1F7" stroke="#8AA9C1" strokeWidth="4" strokeLinejoin="round">
        <path d="M46 112c0-15 12-27 27-27 4-13 16-22 31-22 19 0 35 14 38 32h3c15 0 27 12 27 27s-12 27-27 27H59c-17 0-31-14-31-31 0-5 2-10 6-13z" />
      </g>
      <g stroke="#7FA7C7" strokeWidth="3" strokeLinecap="round">
        <path d="M73 153v12M67 159h12M69 155l8 8M77 155l-8 8" />
        <path d="M100 155v12M94 161h12M96 157l8 8M104 157l-8 8" />
        <path d="M127 153v12M121 159h12M123 155l8 8M131 155l-8 8" />
      </g>
    </svg>
  );
}

function MistArt({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 200 200" className={className} aria-hidden>
      <g fill="#F1E6D0" stroke="#8A7760" strokeWidth="4" strokeLinejoin="round">
        <path d="M46 102c0-15 12-27 27-27 4-13 16-22 31-22 19 0 35 14 38 32h3c15 0 27 12 27 27s-12 27-27 27H59c-17 0-31-14-31-31 0-5 2-10 6-13z" />
      </g>
      <g stroke="#A9B3BC" strokeWidth="4" strokeLinecap="round" opacity="0.9">
        <line x1="42" y1="146" x2="160" y2="146" />
        <line x1="56" y1="162" x2="146" y2="162" />
        <line x1="70" y1="178" x2="132" y2="178" />
      </g>
    </svg>
  );
}

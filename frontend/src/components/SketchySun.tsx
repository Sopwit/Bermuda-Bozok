// Large decorative sun that echoes the sketch's sun icon
export function SketchySun({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 200 200" className={className} aria-hidden>
      <defs>
        <radialGradient id="sunCore" cx="50%" cy="45%" r="55%">
          <stop offset="0%" stopColor="#FFD98A" />
          <stop offset="60%" stopColor="#F4B04A" />
          <stop offset="100%" stopColor="#E8872C" />
        </radialGradient>
        <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="6" result="b" />
          <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>
      <g filter="url(#glow)">
        <circle cx="100" cy="100" r="44" fill="url(#sunCore)" />
      </g>
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
      <circle cx="100" cy="100" r="46" fill="none" stroke="#B33A2E" strokeWidth="2.5" strokeDasharray="1 0" />
    </svg>
  );
}

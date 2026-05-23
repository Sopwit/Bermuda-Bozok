import type { SVGProps } from 'react';
import type { WeatherKind } from '../lib/weather';

export function WeatherIcon({ kind, className = '', ...rest }: { kind: WeatherKind; className?: string } & SVGProps<SVGSVGElement>) {
  const common = { fill: 'none', strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, strokeWidth: 1.6 };
  switch (kind) {
    case 'sun':
      return (
        <svg viewBox="0 0 48 48" className={className} {...rest}>
          <g {...common} stroke="#E8A43A">
            <circle cx="24" cy="24" r="8" fill="#F4C26B" />
            <path d="M24 6v4M24 38v4M6 24h4M38 24h4M11 11l2.8 2.8M34.2 34.2L37 37M11 37l2.8-2.8M34.2 13.8L37 11" />
          </g>
        </svg>
      );
    case 'partly':
      return (
        <svg viewBox="0 0 48 48" className={className} {...rest}>
          <g {...common}>
            <circle cx="18" cy="18" r="6" fill="#F4C26B" stroke="#E8A43A" />
            <path d="M18 8v2M18 26v2M8 18h2M26 18h2M12 12l1.4 1.4M22.6 22.6L24 24M12 24l1.4-1.4M22.6 13.4L24 12" stroke="#E8A43A" />
            <path d="M14 32c0-3 2.5-5 5.5-5 .7-2 2.7-3.5 5-3.5 2.8 0 5 2.2 5 5h1.5c2.5 0 4.5 2 4.5 4.5S33.5 38 31 38H16c-2.2 0-4-1.8-4-4 0-1.1.8-2 2-2z" fill="#EDE3D1" stroke="#8A7760" />
          </g>
        </svg>
      );
    case 'cloud':
      return (
        <svg viewBox="0 0 48 48" className={className} {...rest}>
          <g {...common} stroke="#8A7760">
            <path d="M12 30c0-3.3 2.7-6 6-6 .8-3 3.6-5 6.8-5 3.8 0 6.9 2.9 7.2 6.7h.5c3 0 5.5 2.5 5.5 5.5S35.5 37 32.5 37H14c-2.8 0-5-2.2-5-5 0-1.1.6-2 1.5-2.5" fill="#EDE3D1" />
          </g>
        </svg>
      );
    case 'rain':
      return (
        <svg viewBox="0 0 48 48" className={className} {...rest}>
          <g {...common}>
            <path d="M12 26c0-3.3 2.7-6 6-6 .8-3 3.6-5 6.8-5 3.8 0 6.9 2.9 7.2 6.7h.5c3 0 5.5 2.5 5.5 5.5S35.5 33 32.5 33H14c-2.8 0-5-2.2-5-5 0-1.1.6-2 1.5-2.5" fill="#D8E4EC" stroke="#5B8FB9" />
            <path d="M16 37l-2 4M24 37l-2 4M32 37l-2 4" stroke="#4A7FA3" />
          </g>
        </svg>
      );
    case 'sun-cloud':
      return (
        <svg viewBox="0 0 48 48" className={className} {...rest}>
          <g {...common}>
            <circle cx="32" cy="16" r="6" fill="#F4C26B" stroke="#E8A43A" />
            <path d="M32 6v2M32 24v2M22 16h2M40 16h2" stroke="#E8A43A" />
            <path d="M10 32c0-3 2.5-5.5 5.5-5.5.8-2.5 3-4 5.5-4 3.2 0 5.8 2.5 6 5.7h.5c2.6 0 4.5 2 4.5 4.4S30 37 27.5 37H12.5C10 37 8 35 8 32.5c0-1 .4-1.8 1-2.3" fill="#EDE3D1" stroke="#8A7760" />
          </g>
        </svg>
      );
    case 'moon':
      return (
        <svg viewBox="0 0 48 48" className={className} {...rest}>
          <g {...common} stroke="#5A4635">
            <path d="M30 8c-1.5 0-3 .3-4.3.8A12 12 0 1 0 39.2 22.3C37.5 26.5 33.3 29.5 28.4 29.5 21.8 29.5 16.5 24.2 16.5 17.6c0-4.8 2.8-8.9 6.9-10.8" fill="#F4C26B" />
          </g>
        </svg>
      );
    case 'thunder':
      return (
        <svg viewBox="0 0 48 48" className={className} {...rest}>
          <g {...common}>
            <path d="M12 26c0-3.3 2.7-6 6-6 .8-3 3.6-5 6.8-5 3.8 0 6.9 2.9 7.2 6.7h.5c3 0 5.5 2.5 5.5 5.5S35.5 33 32.5 33H14c-2.8 0-5-2.2-5-5" fill="#C9D1DC" stroke="#5A4635" />
            <path d="M24 30l-3 6h4l-2 6 6-8h-4l2-4z" fill="#E8A43A" stroke="#B07520" />
          </g>
        </svg>
      );
  }
}

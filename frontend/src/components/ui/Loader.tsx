/**
 * Loader éditorial : trois points d'encre qui battent doucement.
 * Remplace le spinner circulaire générique.
 */

interface LoaderProps {
  label?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const dotSize = { sm: 'w-1.5 h-1.5', md: 'w-2 h-2', lg: 'w-2.5 h-2.5' };

export default function Loader({ label, size = 'md', className = '' }: LoaderProps) {
  return (
    <div className={`flex items-center gap-3 ${className}`} role="status" aria-live="polite">
      <span className="flex items-center gap-1.5">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className={`${dotSize[size]} bg-ink inline-block animate-pulse`}
            style={{ animationDelay: `${i * 180}ms`, animationDuration: '1.1s' }}
          />
        ))}
      </span>
      {label && <span className="text-sm text-ink-faint">{label}</span>}
    </div>
  );
}

export { Loader };

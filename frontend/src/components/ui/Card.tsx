/**
 * Carte du design system : surface papier, filet, ombre discrète.
 * `title` + `kicker` optionnels pour l'en-tête éditorial.
 */

import { HTMLAttributes, ReactNode } from 'react';

interface CardProps extends Omit<HTMLAttributes<HTMLDivElement>, 'title'> {
  kicker?: string;
  title?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  padded?: boolean;
}

export default function Card({
  kicker,
  title,
  actions,
  children,
  padded = true,
  className = '',
  ...rest
}: CardProps) {
  return (
    <div
      className={`bg-paper-card border border-ink-line shadow-card ${padded ? 'p-6' : ''} ${className}`}
      {...rest}
    >
      {(kicker || title || actions) && (
        <div className={`flex items-end justify-between gap-4 mb-4 pb-3 rule ${padded ? '' : 'px-6 pt-6'}`}>
          <div>
            {kicker && <p className="kicker mb-1">{kicker}</p>}
            {title && <h2 className="font-display text-xl text-ink">{title}</h2>}
          </div>
          {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
        </div>
      )}
      {children}
    </div>
  );
}

/**
 * Carte statistique — chiffre en Fraunces, étiquette en petites capitales.
 */

import { LucideIcon, TrendingUp, TrendingDown } from 'lucide-react';

interface StatsCardProps {
  title: string;
  value: number | string;
  icon: LucideIcon;
  trend?: {
    value: number;
    direction: 'up' | 'down';
  };
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'purple' | 'orange';
}

// Couleur du filet supérieur selon l'ancienne prop (compat)
const accentStyles = {
  blue: 'border-t-info',
  green: 'border-t-success',
  yellow: 'border-t-warning',
  red: 'border-t-danger',
  purple: 'border-t-accent',
  orange: 'border-t-accent',
};

const trendColors = {
  up: 'text-success',
  down: 'text-danger',
};

export const StatsCard = ({ title, value, icon: Icon, trend, color = 'blue' }: StatsCardProps) => {
  return (
    <div className={`bg-paper-card border border-ink-line border-t-2 ${accentStyles[color]} shadow-card p-5`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="kicker mb-2">{title}</p>
          <p className="font-display text-4xl text-ink figures leading-none">{value}</p>

          {trend && (
            <div className={`flex items-center gap-1 mt-2 text-sm figures ${trendColors[trend.direction]}`}>
              {trend.direction === 'up' ? (
                <TrendingUp className="w-4 h-4" />
              ) : (
                <TrendingDown className="w-4 h-4" />
              )}
              <span>{Math.abs(trend.value)}%</span>
            </div>
          )}
        </div>

        <Icon className="w-5 h-5 text-ink-faint shrink-0" />
      </div>
    </div>
  );
};

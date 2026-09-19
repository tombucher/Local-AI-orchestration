/**
 * Badge réutilisable — étiquette éditoriale : petites capitales, filet coloré.
 */

import { LucideIcon } from 'lucide-react';

interface BadgeProps {
  label: string;
  variant?: 'success' | 'warning' | 'error' | 'info' | 'neutral' | 'professional' | 'personal' | 'research';
  size?: 'sm' | 'md';
  icon?: LucideIcon;
}

const variantStyles = {
  success: 'border-success text-success',
  warning: 'border-warning text-warning',
  error: 'border-danger text-danger',
  info: 'border-info text-info',
  neutral: 'border-ink-line text-ink-faint',
  professional: 'border-info text-info',
  personal: 'border-success text-success',
  research: 'border-accent text-accent',
};

const sizeStyles = {
  sm: 'text-[10px] px-2 py-0.5',
  md: 'text-xs px-2.5 py-1',
};

export const Badge = ({ label, variant = 'neutral', size = 'sm', icon: Icon }: BadgeProps) => {
  return (
    <span
      className={`
        inline-flex items-center gap-1 border bg-paper-card font-semibold uppercase tracking-[0.08em]
        ${variantStyles[variant]}
        ${sizeStyles[size]}
      `}
    >
      {Icon && <Icon className="w-3 h-3" />}
      {label}
    </span>
  );
};

/**
 * Bouton du design system « journal d'atelier ».
 * Variantes : primary (vermillon plein), secondary (filet encre), ghost, danger.
 */

import { ButtonHTMLAttributes, ReactNode } from 'react';
import { Loader } from 'lucide-react';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
type Size = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: ReactNode;
  children?: ReactNode;
}

const variantClasses: Record<Variant, string> = {
  primary:
    'bg-accent text-white hover:bg-accent-deep border border-accent hover:border-accent-deep',
  secondary:
    'bg-transparent text-ink border border-ink hover:bg-ink hover:text-paper',
  ghost:
    'bg-transparent text-ink-soft border border-transparent hover:bg-paper-warm hover:text-ink',
  danger:
    'bg-transparent text-danger border border-danger hover:bg-danger hover:text-white',
};

const sizeClasses: Record<Size, string> = {
  sm: 'px-3 py-1.5 text-xs gap-1.5',
  md: 'px-4 py-2 text-sm gap-2',
  lg: 'px-6 py-3 text-base gap-2.5',
};

export default function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  children,
  className = '',
  disabled,
  ...rest
}: ButtonProps) {
  return (
    <button
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center font-medium uppercase tracking-wide
        transition-colors duration-150 disabled:opacity-40 disabled:cursor-not-allowed
        focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent
        ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
      {...rest}
    >
      {loading ? <Loader className="w-4 h-4 animate-spin" /> : icon}
      {children}
    </button>
  );
}

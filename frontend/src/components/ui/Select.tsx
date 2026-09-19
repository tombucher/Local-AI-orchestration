/**
 * Select du design system, assorti à Input.
 * Compatible react-hook-form via forwardRef.
 */

import { SelectHTMLAttributes, forwardRef } from 'react';

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, className = '', children, ...rest }, ref) => (
    <div>
      {label && (
        <label className="block text-sm font-medium text-ink-soft mb-1">{label}</label>
      )}
      <select
        ref={ref}
        className={`w-full px-3 py-2 bg-paper-card border border-ink-line text-ink text-sm
          focus:outline-none focus:border-ink focus:ring-1 focus:ring-ink
          disabled:opacity-50 transition-colors ${error ? 'border-danger' : ''} ${className}`}
        {...rest}
      >
        {children}
      </select>
      {error && <p className="mt-1 text-sm text-danger" role="alert">{error}</p>}
    </div>
  )
);
Select.displayName = 'Select';

export default Select;

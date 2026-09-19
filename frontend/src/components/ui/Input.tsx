/**
 * Champ texte du design system : fond papier, filet bas marqué au focus.
 * Compatible react-hook-form via forwardRef.
 */

import { InputHTMLAttributes, TextareaHTMLAttributes, forwardRef } from 'react';

const fieldClasses = `w-full px-3 py-2 bg-paper-card border border-ink-line text-ink text-sm
  placeholder:text-ink-faint
  focus:outline-none focus:border-ink focus:ring-1 focus:ring-ink
  disabled:opacity-50 transition-colors`;

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = '', ...rest }, ref) => (
    <div>
      {label && (
        <label className="block text-sm font-medium text-ink-soft mb-1">{label}</label>
      )}
      <input ref={ref} className={`${fieldClasses} ${error ? 'border-danger' : ''} ${className}`} {...rest} />
      {error && <p className="mt-1 text-sm text-danger" role="alert">{error}</p>}
    </div>
  )
);
Input.displayName = 'Input';

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, className = '', ...rest }, ref) => (
    <div>
      {label && (
        <label className="block text-sm font-medium text-ink-soft mb-1">{label}</label>
      )}
      <textarea ref={ref} className={`${fieldClasses} ${error ? 'border-danger' : ''} ${className}`} {...rest} />
      {error && <p className="mt-1 text-sm text-danger" role="alert">{error}</p>}
    </div>
  )
);
Textarea.displayName = 'Textarea';

export default Input;

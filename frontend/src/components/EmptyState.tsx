/**
 * État vide générique avec CTA optionnel — ton éditorial.
 */

import { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon: LucideIcon;
  title?: string;
  description?: string;
  message?: string; // Alternative à title+description
  action?: {
    label: string;
    onClick: () => void;
  };
}

export const EmptyState = ({ icon: Icon, title, description, message, action }: EmptyStateProps) => {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <div className="w-14 h-14 border border-ink-line bg-paper-warm flex items-center justify-center mb-4 rotate-3">
        <Icon className="w-6 h-6 text-ink-faint" />
      </div>

      {message ? (
        <p className="text-sm text-ink-faint text-center max-w-md mb-6">{message}</p>
      ) : (
        <>
          {title && <h3 className="font-display text-xl text-ink mb-2">{title}</h3>}
          {description && <p className="text-sm text-ink-faint text-center max-w-md mb-6">{description}</p>}
        </>
      )}

      {action && (
        <button
          onClick={action.onClick}
          className="px-4 py-2 bg-accent text-white hover:bg-accent-deep transition-colors font-medium text-sm uppercase tracking-wide"
        >
          {action.label}
        </button>
      )}
    </div>
  );
};

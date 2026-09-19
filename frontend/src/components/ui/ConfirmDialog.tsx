/**
 * Modal de confirmation pour les actions destructives.
 * Utilisation :
 *   const [confirmOpen, setConfirmOpen] = useState(false);
 *   <ConfirmDialog open={confirmOpen} title="Supprimer le projet ?" ... />
 */

import { useEffect, useRef } from 'react';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Confirmer',
  cancelLabel = 'Annuler',
  danger = true,
  loading = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const confirmRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    confirmRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onCancel}
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <div
        className="w-full max-w-md bg-paper-card border border-ink-line p-6 shadow-lifted animate-fade-up"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="font-display text-xl text-ink">{title}</h3>
        {message && <p className="mt-2 text-sm text-ink-soft">{message}</p>}
        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={loading}
            className="border border-ink-line px-4 py-2 text-sm font-medium text-ink-soft hover:bg-paper-warm disabled:opacity-50 transition-colors"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            ref={confirmRef}
            onClick={onConfirm}
            disabled={loading}
            className={`px-4 py-2 text-sm font-medium text-white disabled:opacity-50 transition-colors ${
              danger ? 'bg-danger hover:opacity-90' : 'bg-accent hover:bg-accent-deep'
            }`}
          >
            {loading ? 'En cours…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

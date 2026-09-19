/**
 * Modal pour valider, ajuster ou rejeter une tâche
 */

import { useState } from 'react';
import { X, Check, Edit, XCircle } from 'lucide-react';

interface ValidationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (notes?: string) => void;
  type: 'validate' | 'adjust' | 'reject';
  taskTitle: string;
  loading?: boolean;
}

const modalConfig = {
  validate: {
    title: 'Valider le code généré',
    icon: Check,
    iconColor: 'text-success',
    buttonClass: 'bg-success hover:bg-success',
    buttonLabel: 'Valider',
    notesLabel: 'Notes de validation (optionnel)',
    notesPlaceholder: 'Ajoutez des notes sur cette validation...',
  },
  adjust: {
    title: 'Demander un ajustement',
    icon: Edit,
    iconColor: 'text-warning',
    buttonClass: 'bg-warning hover:bg-warning',
    buttonLabel: 'Demander ajustement',
    notesLabel: 'Feedback pour ajustement (requis)',
    notesPlaceholder: 'Décrivez les modifications souhaitées...',
  },
  reject: {
    title: 'Rejeter le code généré',
    icon: XCircle,
    iconColor: 'text-danger',
    buttonClass: 'bg-danger hover:opacity-90 hover:bg-danger',
    buttonLabel: 'Rejeter',
    notesLabel: 'Raison du rejet (requis)',
    notesPlaceholder: 'Expliquez pourquoi ce code est rejeté...',
  },
};

export const ValidationModal = ({
  isOpen,
  onClose,
  onConfirm,
  type,
  taskTitle,
  loading = false,
}: ValidationModalProps) => {
  const [notes, setNotes] = useState('');
  const config = modalConfig[type];
  const Icon = config.icon;
  const notesRequired = type !== 'validate';

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (notesRequired && !notes.trim()) {
      return;
    }
    onConfirm(notes.trim() || undefined);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-paper-card rounded-none shadow-xl max-w-md w-full">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-ink-line">
          <div className="flex items-center gap-3">
            <Icon className={`w-6 h-6 ${config.iconColor}`} />
            <h2 className="text-xl font-semibold text-ink">{config.title}</h2>
          </div>
          <button
            onClick={onClose}
            disabled={loading}
            className="text-ink-faint hover:text-ink-soft transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit}>
          <div className="p-6 space-y-4">
            <div>
              <p className="text-sm text-ink-soft mb-1">Tâche concernée :</p>
              <p className="font-medium text-ink">{taskTitle}</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-ink-soft mb-2">
                {config.notesLabel}
                {notesRequired && <span className="text-danger ml-1">*</span>}
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder={config.notesPlaceholder}
                rows={4}
                maxLength={500}
                className="w-full px-3 py-2 border border-ink-line rounded-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent resize-none"
                disabled={loading}
                required={notesRequired}
              />
              <p className="mt-1 text-xs text-ink-faint">
                {notes.length}/500 caractères
              </p>
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 px-6 py-4 bg-paper rounded-b-lg">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 text-ink-soft bg-paper-card border border-ink-line rounded-none hover:bg-paper-warm transition-colors disabled:opacity-50"
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={loading || (notesRequired && !notes.trim())}
              className={`px-4 py-2 text-white rounded-none transition-colors disabled:opacity-50 ${config.buttonClass}`}
            >
              {loading ? 'Traitement...' : config.buttonLabel}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

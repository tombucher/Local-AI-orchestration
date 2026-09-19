/**
 * Panneau d'actions en revue manuelle : valider, regénérer avec instructions,
 * demander un ajustement, rejeter.
 */

import { Check, RefreshCw, Send, XCircle } from 'lucide-react';

interface TaskReviewActionsProps {
  validateLabel: string;
  actionLoading: boolean;
  showRegenInput: boolean;
  regenInstructions: string;
  onRegenInstructionsChange: (value: string) => void;
  onToggleRegenInput: (open: boolean) => void;
  onRegenerate: () => void;
  onValidate: () => void;
  onAdjust: () => void;
  onReject: () => void;
}

const full = 'w-full flex items-center justify-center gap-2 px-4 py-2 text-white transition-colors disabled:opacity-50';

export const TaskReviewActions = ({
  validateLabel, actionLoading, showRegenInput, regenInstructions,
  onRegenInstructionsChange, onToggleRegenInput, onRegenerate, onValidate, onAdjust, onReject,
}: TaskReviewActionsProps) => (
  <div className="bg-paper-card shadow-card border border-ink-line p-6">
    <h2 className="font-display text-xl text-ink mb-4">Actions de validation</h2>
    <div className="space-y-3">
      <button onClick={onValidate} disabled={actionLoading} className={`${full} bg-success hover:opacity-90`}>
        <Check className="w-4 h-4" />
        {validateLabel}
      </button>

      {!showRegenInput ? (
        <button onClick={() => onToggleRegenInput(true)} disabled={actionLoading} className={`${full} bg-accent hover:bg-accent-deep`}>
          <Send className="w-4 h-4" />
          Regénérer avec instructions
        </button>
      ) : (
        <div className="border border-ink-line p-3 bg-paper">
          <textarea
            value={regenInstructions}
            onChange={(e) => onRegenInstructionsChange(e.target.value)}
            placeholder="Ex : utilise TypeScript au lieu de Python, ajoute des tests unitaires…"
            rows={3}
            maxLength={1000}
            className="w-full px-3 py-2 text-sm bg-paper-card border border-ink-line focus:outline-none focus:border-ink focus:ring-1 focus:ring-ink resize-none"
            disabled={actionLoading}
          />
          <div className="flex gap-2 mt-2">
            <button
              onClick={onRegenerate}
              disabled={actionLoading || !regenInstructions.trim()}
              className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 text-sm bg-accent text-white hover:bg-accent-deep disabled:opacity-50"
            >
              <Send className="w-3 h-3" />
              Lancer
            </button>
            <button
              onClick={() => { onToggleRegenInput(false); onRegenInstructionsChange(''); }}
              className="px-3 py-1.5 text-sm text-ink-soft bg-paper-card border border-ink-line hover:bg-paper-warm"
            >
              Annuler
            </button>
          </div>
        </div>
      )}

      <button onClick={onAdjust} disabled={actionLoading} className={`${full} bg-warning hover:opacity-90`}>
        <RefreshCw className="w-4 h-4" />
        Demander un ajustement
      </button>
      <button onClick={onReject} disabled={actionLoading} className={`${full} bg-danger hover:opacity-90`}>
        <XCircle className="w-4 h-4" />
        Rejeter
      </button>
    </div>
  </div>
);

/**
 * Bloc d'état et d'actions d'une tâche selon son statut :
 * CREATED / READY / GENERATING / FAILED / CANCELLED.
 * (MANUAL_REVIEW et COMPLETED sont composés dans la page avec TaskResultPanel.)
 */

import { CheckCircle2, ListPlus, Play, RefreshCw, StopCircle } from 'lucide-react';
import type { Task } from '../../types/task.types';
import { TaskStatus } from '../../types/task.types';
import { isTextTask, isVeilleTask } from './taskTypeUtils';
import Loader from '../ui/Loader';

interface TaskStatusPanelProps {
  task: Task;
  actionLoading: boolean;
  elapsedTime: number;
  onGenerate: () => void;
  onActivate: () => void;
  onComplete: () => void;
  onStopGeneration: () => void;
  onRetry: () => void;
}

const btn = {
  primary: 'flex items-center gap-2 px-4 py-2 bg-accent text-white hover:bg-accent-deep transition-colors disabled:opacity-50',
  secondary: 'flex items-center gap-2 px-4 py-2 bg-paper-card border border-ink text-ink hover:bg-paper-warm transition-colors disabled:opacity-50',
  success: 'flex items-center gap-2 px-4 py-2 bg-paper-card border border-success text-success hover:bg-success/10 transition-colors disabled:opacity-50',
  danger: 'flex items-center justify-center gap-2 px-4 py-2 bg-danger text-white hover:opacity-90 transition-colors disabled:opacity-50',
};

const CompleteButton = ({ onClick, disabled }: { onClick: () => void; disabled: boolean }) => (
  <button onClick={onClick} disabled={disabled} className={btn.success}>
    <CheckCircle2 className="w-4 h-4" />
    Marquer comme terminée
  </button>
);

export const TaskStatusPanel = ({
  task, actionLoading, elapsedTime, onGenerate, onActivate, onComplete, onStopGeneration, onRetry,
}: TaskStatusPanelProps) => {
  const veille = isVeilleTask(task.task_type);

  if (task.status === TaskStatus.CREATED) {
    return (
      <div className="bg-paper border border-ink-line p-6">
        <p className="text-ink mb-4">Tâche créée mais pas encore activée. Choisis une action :</p>
        <div className="flex flex-wrap gap-3">
          <button onClick={onGenerate} disabled={actionLoading} className={btn.primary}>
            <Play className="w-4 h-4" />
            {veille ? 'Lancer la veille maintenant' : 'Générer maintenant'}
          </button>
          <button onClick={onActivate} disabled={actionLoading} className={btn.secondary}>
            <ListPlus className="w-4 h-4" />
            Mettre en file (auto)
          </button>
          <CompleteButton onClick={onComplete} disabled={actionLoading} />
        </div>
      </div>
    );
  }

  if (task.status === TaskStatus.READY) {
    return (
      <div className="bg-info/5 border border-info/30 p-6">
        <p className="text-info mb-4">Tâche prête. En attente de traitement par l'orchestrateur.</p>
        {(task.retry_count ?? 0) > 0 && task.validation_notes && (
          <div className="mb-4 p-3 bg-paper-card border border-warning/50 text-sm text-ink-soft">
            <p className="font-semibold text-warning mb-1">
              ⚠️ La tentative précédente a échoué ({task.retry_count}/3)
            </p>
            <p>{task.validation_notes}</p>
          </div>
        )}
        <div className="flex flex-wrap gap-3">
          <button onClick={onGenerate} disabled={actionLoading} className={btn.primary}>
            <Play className="w-4 h-4" />
            {veille ? 'Lancer la veille' : 'Générer maintenant'}
          </button>
          <CompleteButton onClick={onComplete} disabled={actionLoading} />
        </div>
      </div>
    );
  }

  if (task.status === TaskStatus.GENERATING) {
    return (
      <div className="bg-warning/5 border border-warning/30 p-6">
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <Loader size="lg" />
            <p className="text-warning font-medium">
              {veille ? 'Veille en cours…' : isTextTask(task.task_type) ? 'Génération du contenu en cours…' : 'Le modèle génère le code…'}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-highlight/40 h-1.5 overflow-hidden">
              <div className="bg-warning h-full animate-pulse" style={{ width: '60%' }} />
            </div>
            <span className="text-sm text-warning font-mono min-w-[80px] text-right figures">
              {Math.floor(elapsedTime / 60)}:{(elapsedTime % 60).toString().padStart(2, '0')}
            </span>
          </div>
          <p className="text-sm text-ink-soft">
            Compte quelques minutes selon le modèle. La page se rafraîchit toute seule.
          </p>
          <button onClick={onStopGeneration} disabled={actionLoading} className={btn.danger}>
            <StopCircle className="w-4 h-4" />
            Arrêter la génération
          </button>
        </div>
      </div>
    );
  }

  if (task.status === TaskStatus.FAILED || task.status === TaskStatus.CANCELLED) {
    const failed = task.status === TaskStatus.FAILED;
    return (
      <div className={`border p-6 ${failed ? 'bg-danger/5 border-danger/30' : 'bg-paper border-ink-line'}`}>
        <p className={`font-medium mb-2 ${failed ? 'text-danger' : 'text-ink'}`}>
          {failed ? 'La génération a échoué.' : 'Cette tâche a été annulée.'}
        </p>
        {task.validation_notes && (
          <p className="text-sm text-ink-soft mb-4 bg-paper-card p-3 border border-ink-line">{task.validation_notes}</p>
        )}
        <div className="flex flex-wrap gap-3">
          <button onClick={onRetry} disabled={actionLoading} className={btn.primary}>
            <RefreshCw className="w-4 h-4" />
            Relancer
          </button>
          <CompleteButton onClick={onComplete} disabled={actionLoading} />
        </div>
      </div>
    );
  }

  return null;
};

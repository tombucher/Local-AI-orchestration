/**
 * Page Détail Tâche — composition :
 * - TaskHeader (titre, badges, actions)
 * - TaskStatusPanel (CREATED / READY / GENERATING / FAILED / CANCELLED)
 * - TaskReviewActions + TaskResultPanel (MANUAL_REVIEW)
 * - TaskResultPanel (COMPLETED)
 * L'état et les appels API restent ici ; les sous-composants sont purement visuels.
 */

import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ChevronRight, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';
import { useTasksStore } from '../../stores/tasksStore';
import { useTimerStore } from '../../stores/timerStore';
import { Navbar } from '../../components/Layout/Navbar';
import { Sidebar } from '../../components/Layout/Sidebar';
import { ValidationModal } from '../../components/tasks/ValidationModal';
import { TaskHeader } from '../../components/tasks/TaskHeader';
import { TaskStatusPanel } from '../../components/tasks/TaskStatusPanel';
import { TaskReviewActions } from '../../components/tasks/TaskReviewActions';
import { TaskResultPanel, hasGeneratedContent } from '../../components/tasks/TaskResultPanel';
import { getValidateLabel, isTextTask, isVeilleTask } from '../../components/tasks/taskTypeUtils';
import ConfirmDialog from '../../components/ui/ConfirmDialog';
import InkLoader from '../../components/ui/Loader';
import { TaskStatus, TaskType } from '../../types/task.types';
import type { VeilleResult, VeilleRefinePayload } from '../../types/task.types';
import { tasksService } from '../../services/tasks';
import { usePolling } from '../../hooks/usePolling';

type ModalType = 'validate' | 'adjust' | 'reject' | null;
type PendingConfirm = { title: string; message?: string; confirmLabel?: string; onConfirm: () => Promise<void> } | null;

const PageShell = ({ children }: { children: React.ReactNode }) => (
  <div className="min-h-screen bg-paper">
    <Navbar />
    <div className="flex">
      <Sidebar />
      <main className="flex-1 p-6 lg:p-8">{children}</main>
    </div>
  </div>
);

export const TaskDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const {
    currentTask, loading, fetchTask, validateTask, rejectTask, generateTask,
    deleteTask, stopGeneration, retryTask, activateTask, completeTask,
  } = useTasksStore();
  const { currentTimer: activeTimer, startTimer } = useTimerStore();

  const [modalType, setModalType] = useState<ModalType>(null);
  const [confirm, setConfirm] = useState<PendingConfirm>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);

  // Édition inline et regénération avec instructions
  const [isEditing, setIsEditing] = useState(false);
  const [editedCode, setEditedCode] = useState('');
  const [regenInstructions, setRegenInstructions] = useState('');
  const [showRegenInput, setShowRegenInput] = useState(false);

  // Résultats de veille / financements
  const [veilleResults, setVeilleResults] = useState<VeilleResult[]>([]);
  const [veilleTotal, setVeilleTotal] = useState(0);
  const [veilleLoading, setVeilleLoading] = useState(false);

  useEffect(() => {
    if (id) fetchTask(parseInt(id));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // Résultats de veille : tâches veille et recherche de financements, une fois terminées
  useEffect(() => {
    const hasVeilleResults = !!currentTask &&
      (isVeilleTask(currentTask.task_type) || currentTask.task_type === TaskType.FUNDING_SEARCH);
    if (!currentTask || !hasVeilleResults) {
      setVeilleResults([]);
      setVeilleTotal(0);
      return;
    }
    if (currentTask.status === TaskStatus.MANUAL_REVIEW || currentTask.status === TaskStatus.COMPLETED) {
      setVeilleLoading(true);
      tasksService.getVeilleResults(currentTask.id)
        .then((data) => { setVeilleResults(data.items); setVeilleTotal(data.total); })
        .catch((err) => console.error('Erreur chargement résultats veille:', err))
        .finally(() => setVeilleLoading(false));
    }
  }, [currentTask?.id, currentTask?.task_type, currentTask?.status]);

  // Rafraîchissement pendant la génération (pause quand l'onglet est caché)
  const isGenerating = currentTask?.status === TaskStatus.GENERATING;
  usePolling(() => { if (id) fetchTask(parseInt(id)); }, 3000, { enabled: isGenerating, immediate: false });

  useEffect(() => {
    if (!isGenerating) { setElapsedTime(0); return; }
    const timer = setInterval(() => setElapsedTime((t) => t + 1), 1000);
    return () => clearInterval(timer);
  }, [isGenerating]);

  if (loading && !currentTask) {
    return (
      <PageShell>
        <div className="flex items-center justify-center py-12"><InkLoader size="lg" /></div>
      </PageShell>
    );
  }

  if (!currentTask) {
    return (
      <PageShell>
        <div className="text-center py-12">
          <p className="text-ink-faint">Tâche non trouvée</p>
          <Link to="/tasks" className="mt-4 inline-block text-accent hover:underline">Retour aux tâches</Link>
        </div>
      </PageShell>
    );
  }

  const task = currentTask;
  const refresh = async () => { if (id) await fetchTask(parseInt(id)); };

  /** Enveloppe commune : verrou d'action + toast de succès (l'erreur est toastée par l'intercepteur) */
  const run = async (fn: () => Promise<void>, successMessage?: string) => {
    setActionLoading(true);
    try {
      await fn();
      if (successMessage) toast.success(successMessage);
    } catch {
      // déjà toastée
    } finally {
      setActionLoading(false);
    }
  };

  const handleValidate = (notes?: string) => run(async () => {
    await validateTask(task.id, true, notes, isEditing ? editedCode : undefined);
    setModalType(null);
    setIsEditing(false);
  }, isEditing ? 'Validé avec tes modifications' : 'Résultat validé');

  const handleAdjust = (notes?: string) => run(async () => {
    await rejectTask(task.id, notes || 'Ajustement demandé');
    setModalType(null);
    await refresh();
  }, "Demande d'ajustement envoyée");

  const handleReject = (notes?: string) => run(async () => {
    await rejectTask(task.id, notes || 'Résultat rejeté');
    setModalType(null);
    await refresh();
  }, 'Résultat rejeté');

  const handleRegenerate = () => run(async () => {
    if (!regenInstructions.trim()) return;
    await rejectTask(task.id, regenInstructions.trim());
    await generateTask(task.id);
    setShowRegenInput(false);
    setRegenInstructions('');
    await refresh();
  }, 'Regénération lancée avec tes instructions');

  const handleGenerate = () => run(async () => {
    await generateTask(task.id);
  }, isVeilleTask(task.task_type)
      ? 'Veille lancée ! Les résultats arrivent dans quelques minutes.'
      : isTextTask(task.task_type)
      ? 'Génération lancée ! Le contenu sera prêt dans quelques minutes.'
      : 'Génération lancée ! Le code arrive dans quelques minutes.');

  const handleRetry = () => run(async () => { await retryTask(task.id); await refresh(); }, 'Tâche relancée — prête pour génération');
  const handleActivate = () => run(async () => { await activateTask(task.id); }, 'Tâche mise en file — le scheduler la traitera');

  const handleStopGeneration = () => setConfirm({
    title: 'Arrêter la génération ?',
    message: 'La tâche repassera en attente ; le travail en cours sera perdu.',
    confirmLabel: 'Arrêter',
    onConfirm: () => run(async () => { await stopGeneration(task.id); }, 'Génération arrêtée'),
  });

  const handleComplete = () => setConfirm({
    title: 'Marquer comme terminée ?',
    message: 'La tâche passera en « terminée » sans contenu généré supplémentaire.',
    confirmLabel: 'Terminer',
    onConfirm: () => run(async () => { await completeTask(task.id); }),
  });

  const handleDelete = () => setConfirm({
    title: 'Supprimer cette tâche ?',
    message: `« ${task.title} » sera supprimée définitivement.`,
    confirmLabel: 'Supprimer',
    onConfirm: () => run(async () => { await deleteTask(task.id); navigate('/tasks'); }, 'Tâche supprimée'),
  });

  const handleStartTimer = () => run(async () => { await startTimer(task.project_id, task.id); }, 'Chrono démarré sur cette tâche');

  const handleVeilleRefine = async (refinement: VeilleRefinePayload) => {
    await tasksService.refineVeille(task.id, refinement);
    toast.success('Affinage appliqué ! Les prochaines occurrences utiliseront ces paramètres.');
  };

  const resultPanel = (
    <TaskResultPanel
      task={task}
      veilleResults={veilleResults}
      veilleTotal={veilleTotal}
      veilleLoading={veilleLoading}
      isEditing={isEditing}
      editedCode={editedCode}
      onEditedCodeChange={setEditedCode}
      onStartEditing={() => { setIsEditing(true); setEditedCode(task.generated_code || ''); }}
      onCancelEditing={() => { setIsEditing(false); setEditedCode(''); }}
      onRefine={handleVeilleRefine}
    />
  );

  return (
    <PageShell>
      {/* Fil d'Ariane */}
      <div className="flex items-center gap-2 text-sm mb-6">
        <Link to="/dashboard" className="text-ink-soft hover:text-accent">Accueil</Link>
        <ChevronRight className="w-4 h-4 text-ink-faint" />
        <Link to="/tasks" className="text-ink-soft hover:text-accent">Tâches</Link>
        <ChevronRight className="w-4 h-4 text-ink-faint" />
        <span className="text-ink">{task.title}</span>
      </div>

      <TaskHeader
        task={task}
        canStartTimer={!activeTimer}
        onStartTimer={handleStartTimer}
        onEdit={() => navigate(`/tasks/${task.id}/edit`)}
        onDelete={handleDelete}
      />

      {/* Revue manuelle : informations + actions à gauche, contenu à droite */}
      {task.status === TaskStatus.MANUAL_REVIEW && hasGeneratedContent(task, veilleResults) && (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 mb-6">
          <div className="lg:col-span-2 space-y-6">
            {task.llm_prompt && (
              <div className="bg-paper-card shadow-card border border-ink-line p-6">
                <p className="kicker mb-2">Prompt utilisé</p>
                <p className="text-sm text-ink-soft bg-paper p-3 border border-ink-line">{task.llm_prompt}</p>
              </div>
            )}
            <TaskReviewActions
              validateLabel={isEditing ? 'Valider avec modifications' : getValidateLabel(task.task_type)}
              actionLoading={actionLoading}
              showRegenInput={showRegenInput}
              regenInstructions={regenInstructions}
              onRegenInstructionsChange={setRegenInstructions}
              onToggleRegenInput={setShowRegenInput}
              onRegenerate={handleRegenerate}
              onValidate={() => setModalType('validate')}
              onAdjust={() => setModalType('adjust')}
              onReject={() => setModalType('reject')}
            />
          </div>
          <div className="lg:col-span-3">{resultPanel}</div>
        </div>
      )}

      <TaskStatusPanel
        task={task}
        actionLoading={actionLoading}
        elapsedTime={elapsedTime}
        onGenerate={handleGenerate}
        onActivate={handleActivate}
        onComplete={handleComplete}
        onStopGeneration={handleStopGeneration}
        onRetry={handleRetry}
      />

      {task.status === TaskStatus.COMPLETED && (
        <div className="space-y-6">
          {hasGeneratedContent(task, veilleResults) ? resultPanel : (
            <div className="bg-success/5 border border-success/30 p-6">
              <p className="text-success font-medium">✅ Tâche terminée</p>
              <p className="text-sm text-ink-soft mt-1">Cette tâche a été marquée comme terminée sans contenu généré.</p>
            </div>
          )}
          {task.validation_notes && (
            <div className="bg-paper-card shadow-card border border-ink-line p-6">
              <p className="kicker mb-2">Notes de validation</p>
              <p className="text-sm text-ink-soft">{task.validation_notes}</p>
            </div>
          )}
          {isVeilleTask(task.task_type) && (
            <div className="bg-info/5 border border-info/30 p-4 flex items-center justify-between gap-4">
              <p className="text-sm text-info">Nouveau scan pour actualiser les résultats ?</p>
              <button
                onClick={handleGenerate}
                disabled={actionLoading}
                className="flex items-center gap-2 px-4 py-2 bg-accent text-white hover:bg-accent-deep transition-colors disabled:opacity-50 text-sm font-medium"
              >
                <RefreshCw className="w-4 h-4" />
                Relancer la veille
              </button>
            </div>
          )}
        </div>
      )}

      <ValidationModal
        isOpen={modalType !== null}
        onClose={() => setModalType(null)}
        onConfirm={modalType === 'validate' ? handleValidate : modalType === 'adjust' ? handleAdjust : handleReject}
        type={modalType || 'validate'}
        taskTitle={task.title}
        loading={actionLoading}
      />

      <ConfirmDialog
        open={confirm !== null}
        title={confirm?.title ?? ''}
        message={confirm?.message}
        confirmLabel={confirm?.confirmLabel}
        loading={actionLoading}
        onCancel={() => setConfirm(null)}
        onConfirm={async () => { const c = confirm; setConfirm(null); if (c) await c.onConfirm(); }}
      />
    </PageShell>
  );
};

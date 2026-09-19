/**
 * Page d'analyse intelligente de projet avec suggestions IA
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Navbar } from '../../components/Layout/Navbar';
import { Sidebar } from '../../components/Layout/Sidebar';
import { TaskTypeBadge } from '../../components/tasks/TaskTypeBadge';
import { api } from '../../services/api';
import { ProjectAnalysis, TaskSuggestion, RefineTaskRequest } from '../../types/project-analysis.types';
import { TaskPriority } from '../../types/task.types';
import toast from 'react-hot-toast';
import { Sparkles, X } from 'lucide-react';
import Loader from '../../components/ui/Loader';

export const ProjectAnalysisPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const projectId = parseInt(id || '0');

  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [analysis, setAnalysis] = useState<ProjectAnalysis | null>(null);
  const [selectedTasks, setSelectedTasks] = useState<Set<number>>(new Set());

  // Modal de raffinement
  const [refineModalOpen, setRefineModalOpen] = useState(false);
  const [taskToRefine, setTaskToRefine] = useState<{ task: TaskSuggestion; index: number } | null>(null);
  const [refinePrompt, setRefinePrompt] = useState('');
  const [refining, setRefining] = useState(false);

  // Charger l'analyse
  const loadAnalysis = async () => {
    setLoading(true);
    try {
      const response = await api.post(`/projects/${projectId}/analyze`, {});
      setAnalysis(response.data);

      // Pré-sélectionner les tâches P1 et P2
      const preselected = new Set<number>();
      response.data.task_suggestions.forEach((task: TaskSuggestion, index: number) => {
        if (task.priority === TaskPriority.P1 || task.priority === TaskPriority.P2) {
          preselected.add(index);
        }
      });
      setSelectedTasks(preselected);

      toast.success('Analyse terminée !');
    } catch (error) {
      console.error('Error loading analysis:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (projectId) {
      loadAnalysis();
    }
  }, [projectId]);

  // Toggle sélection d'une tâche
  const toggleTask = (index: number) => {
    const newSelected = new Set(selectedTasks);
    if (newSelected.has(index)) {
      newSelected.delete(index);
    } else {
      newSelected.add(index);
    }
    setSelectedTasks(newSelected);
  };

  // Sélectionner/Désélectionner tout
  const toggleAll = () => {
    if (selectedTasks.size === analysis?.task_suggestions.length) {
      setSelectedTasks(new Set());
    } else {
      const allIndices = new Set(
        analysis?.task_suggestions.map((_, index) => index) || []
      );
      setSelectedTasks(allIndices);
    }
  };

  // Créer les tâches sélectionnées
  const createTasks = async () => {
    if (selectedTasks.size === 0) {
      toast.error('Sélectionnez au moins une tâche');
      return;
    }

    setCreating(true);
    try {
      // Envoie les suggestions complètes (l'ancien mode par indices relançait
      // toute l'analyse LLM côté backend, lent et non déterministe)
      const response = await api.post(`/projects/${projectId}/create-suggested-tasks`, {
        tasks: Array.from(selectedTasks).map((idx) => analysis!.task_suggestions[idx]),
        veille: analysis?.veille_suggestions ?? [],
      });

      toast.success(response.data.message);
      navigate(`/projects/${projectId}`);
    } catch (error) {
      console.error('Error creating tasks:', error);
    } finally {
      setCreating(false);
    }
  };

  // Ouvrir le modal de raffinement
  const openRefineModal = (task: TaskSuggestion, index: number, e: React.MouseEvent) => {
    e.stopPropagation(); // Empêcher le toggle de sélection
    setTaskToRefine({ task, index });
    setRefineModalOpen(true);
    setRefinePrompt('');
  };

  // Raffiner une tâche avec l'IA
  const refineTask = async () => {
    if (!taskToRefine || !refinePrompt.trim()) {
      toast.error('Veuillez saisir vos instructions');
      return;
    }

    setRefining(true);
    try {
      const request: RefineTaskRequest = {
        task_data: taskToRefine.task,
        user_prompt: refinePrompt,
      };

      const response = await api.post('/projects/refine-task', request);
      const refinedTask = response.data.refined_task;

      // Mettre à jour la tâche dans l'analyse
      if (analysis) {
        const updatedSuggestions = [...analysis.task_suggestions];
        updatedSuggestions[taskToRefine.index] = refinedTask;
        setAnalysis({
          ...analysis,
          task_suggestions: updatedSuggestions,
        });
      }

      toast.success('Tâche raffinée avec succès !');
      setRefineModalOpen(false);
      setTaskToRefine(null);
      setRefinePrompt('');
    } catch (error) {
      console.error('Error refining task:', error);
      toast.error('Erreur lors du raffinement');
    } finally {
      setRefining(false);
    }
  };

  // Icône de priorité
  const getPriorityIcon = (priority: TaskPriority) => {
    switch (priority) {
      case TaskPriority.P1:
        return '🔴';
      case TaskPriority.P2:
        return '🟡';
      case TaskPriority.P3:
        return '🟢';
      default:
        return '⚪';
    }
  };

  // Icône de sévérité de blocage
  const getBlockerSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'bg-danger/10 text-danger';
      case 'medium':
        return 'bg-warning/10 text-warning';
      case 'low':
        return 'bg-info/10 text-info';
      default:
        return 'bg-paper-warm text-ink';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-paper">
        <Navbar />
        <div className="flex">
          <Sidebar />
          <main className="flex-1 p-6 lg:p-8">
            <div className="flex items-center justify-center py-12">
              <Loader size="lg" />
              <span className="ml-4 text-lg">Analyse en cours avec l'IA...</span>
            </div>
          </main>
        </div>
      </div>
    );
  }

  if (!analysis) {
    return null;
  }

  return (
    <div className="min-h-screen bg-paper">
      <Navbar />

      <div className="flex">
        <Sidebar />

        <main className="flex-1 p-6 lg:p-8">
          <div className="max-w-6xl mx-auto">
            {/* Header */}
            <div className="mb-8">
              <button
                onClick={() => navigate(`/projects/${projectId}`)}
                className="text-ink-soft hover:text-ink mb-4"
              >
                ← Retour au projet
              </button>
              <h1 className="text-3xl font-bold text-ink">
                Analyse Intelligente du Projet
              </h1>
              <p className="text-ink-soft mt-2">{analysis.summary}</p>
            </div>

            {/* Statistiques */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
              <div className="bg-paper-card p-4 rounded-none border border-ink-line">
                <div className="text-sm text-ink-soft">Tâches suggérées</div>
                <div className="text-2xl font-bold text-ink">
                  {analysis.task_suggestions.length}
                </div>
              </div>
              <div className="bg-paper-card p-4 rounded-none border border-ink-line">
                <div className="text-sm text-ink-soft">Veilles suggérées</div>
                <div className="text-2xl font-bold text-ink">
                  {analysis.veille_suggestions.length}
                </div>
              </div>
              <div className="bg-paper-card p-4 rounded-none border border-ink-line">
                <div className="text-sm text-ink-soft">Blocages détectés</div>
                <div className="text-2xl font-bold text-danger">
                  {analysis.blockers.length}
                </div>
              </div>
              <div className="bg-paper-card p-4 rounded-none border border-ink-line">
                <div className="text-sm text-ink-soft">Temps estimé</div>
                <div className="text-2xl font-bold text-ink">
                  {analysis.estimated_total_hours || 0}h
                </div>
              </div>
            </div>

            {/* Blocages */}
            {analysis.blockers.length > 0 && (
              <div className="bg-paper-card rounded-none border border-ink-line p-6 mb-8">
                <h2 className="text-lg font-semibold text-ink mb-4">
                  ⚠️ Blocages Détectés
                </h2>
                <div className="space-y-4">
                  {analysis.blockers.map((blocker, index) => (
                    <div
                      key={index}
                      className={`p-4 rounded-none ${getBlockerSeverityColor(blocker.severity)}`}
                    >
                      <div className="font-medium">{blocker.description}</div>
                      <div className="text-sm mt-2">
                        💡 <strong>Solution:</strong> {blocker.suggestion}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Actions prioritaires */}
            {analysis.next_actions.length > 0 && (
              <div className="bg-info/5 rounded-none border border-info/30 p-6 mb-8">
                <h2 className="text-lg font-semibold text-ink mb-4">
                  🎯 Top 3 Actions Prioritaires
                </h2>
                <ol className="list-decimal list-inside space-y-2">
                  {analysis.next_actions.map((action, index) => (
                    <li key={index} className="text-ink">
                      {action}
                    </li>
                  ))}
                </ol>
              </div>
            )}

            {/* Tâches suggérées */}
            <div className="bg-paper-card rounded-none border border-ink-line p-6 mb-8">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-ink">
                  ✨ Tâches Suggérées ({selectedTasks.size}/{analysis.task_suggestions.length} sélectionnées)
                </h2>
                <button
                  onClick={toggleAll}
                  className="text-sm text-primary hover:underline"
                >
                  {selectedTasks.size === analysis.task_suggestions.length
                    ? 'Tout désélectionner'
                    : 'Tout sélectionner'}
                </button>
              </div>

              <div className="space-y-3 max-h-[600px] overflow-y-auto">
                {analysis.task_suggestions.map((task, index) => (
                  <div
                    key={index}
                    className={`border rounded-none p-4 cursor-pointer transition-colors ${
                      selectedTasks.has(index)
                        ? 'border-primary bg-primary/5'
                        : 'border-ink-line hover:border-ink-line'
                    }`}
                    onClick={() => toggleTask(index)}
                  >
                    <div className="flex items-start gap-3">
                      <input
                        type="checkbox"
                        checked={selectedTasks.has(index)}
                        onChange={() => toggleTask(index)}
                        className="mt-1"
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-lg">{getPriorityIcon(task.priority)}</span>
                          <h3 className="font-medium text-ink">{task.title}</h3>
                          <TaskTypeBadge taskType={task.task_type} />
                          {task.estimated_duration && (
                            <span className="text-sm text-ink-faint">
                              ~{task.estimated_duration}h
                            </span>
                          )}
                          <button
                            onClick={(e) => openRefineModal(task, index, e)}
                            className="ml-auto px-2 py-1 text-xs bg-accent-wash text-accent-deep hover:bg-accent-wash rounded flex items-center gap-1 transition-colors"
                            title="Affiner avec l'IA"
                          >
                            <Sparkles className="w-3 h-3" />
                            Affiner
                          </button>
                        </div>
                        <p className="text-sm text-ink-soft mb-2">{task.description}</p>
                        {task.subtasks.length > 0 && (
                          <div className="mt-2 text-sm">
                            <div className="font-medium text-ink-soft mb-1">
                              Sous-tâches:
                            </div>
                            <ul className="space-y-1">
                              {task.subtasks.map((subtask, subIndex) => (
                                <li key={subIndex} className="text-ink-soft">
                                  • {subtask}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Veilles suggérées */}
            {analysis.veille_suggestions.length > 0 && (
              <div className="bg-paper-card rounded-none border border-ink-line p-6 mb-8">
                <h2 className="text-lg font-semibold text-ink mb-4">
                  🔍 Veilles Automatiques Suggérées
                </h2>
                <p className="text-sm text-ink-soft mb-4">
                  Ces veilles seront créées automatiquement lorsque vous créerez les tâches.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {analysis.veille_suggestions.map((veille, index) => (
                    <div
                      key={index}
                      className="border border-ink-line rounded-none p-4"
                    >
                      <div className="font-medium text-ink mb-1">
                        {veille.scope} ({veille.scan_frequency})
                      </div>
                      <div className="text-sm text-ink-soft mb-2">
                        {veille.reason}
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {veille.keywords.map((keyword, kIndex) => (
                          <span
                            key={kIndex}
                            className="text-xs px-2 py-1 bg-paper-warm text-ink-soft rounded"
                          >
                            {keyword}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-4">
              <button
                onClick={() => navigate(`/projects/${projectId}`)}
                className="flex-1 px-4 py-2 border border-ink-line text-ink-soft rounded-none hover:bg-paper-warm transition-colors font-medium"
              >
                Annuler
              </button>
              <button
                onClick={() => loadAnalysis()}
                disabled={loading}
                className="flex-1 px-4 py-2 border border-ink-line text-ink-soft rounded-none hover:bg-paper-warm transition-colors font-medium"
              >
                Re-analyser
              </button>
              <button
                onClick={createTasks}
                disabled={creating || selectedTasks.size === 0}
                className="flex-1 px-4 py-2 bg-primary text-white rounded-none hover:bg-primary/90 transition-colors font-medium disabled:opacity-50"
              >
                {creating ? 'Création...' : `Créer ${selectedTasks.size} tâche(s)`}
              </button>
            </div>
          </div>
        </main>
      </div>

      {/* Modal de raffinement */}
      {refineModalOpen && taskToRefine && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-paper-card rounded-none max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              {/* Header */}
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-ink flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-accent" />
                  Affiner la tâche avec l'IA
                </h2>
                <button
                  onClick={() => setRefineModalOpen(false)}
                  className="text-ink-faint hover:text-ink-soft"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Tâche actuelle */}
              <div className="bg-paper rounded-none p-4 mb-4">
                <h3 className="font-medium text-ink mb-2">{taskToRefine.task.title}</h3>
                <p className="text-sm text-ink-soft">{taskToRefine.task.description}</p>
                {taskToRefine.task.subtasks.length > 0 && (
                  <div className="mt-2">
                    <div className="text-sm font-medium text-ink-soft mb-1">Sous-tâches actuelles:</div>
                    <ul className="text-sm text-ink-soft space-y-1">
                      {taskToRefine.task.subtasks.map((subtask, idx) => (
                        <li key={idx}>• {subtask}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Instructions */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-ink-soft mb-2">
                  Comment voulez-vous affiner cette tâche ?
                </label>
                <textarea
                  value={refinePrompt}
                  onChange={(e) => setRefinePrompt(e.target.value)}
                  placeholder="Ex: Ajoute plus de sous-tâches détaillées
Précise les technologies à utiliser
Augmente la durée estimée
Décompose en tâches plus petites"
                  className="w-full px-3 py-2 border border-ink-line rounded-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  rows={5}
                />
                <p className="text-xs text-ink-faint mt-1">
                  L'IA va générer une version améliorée de la tâche selon vos instructions
                </p>
              </div>

              {/* Actions */}
              <div className="flex gap-3">
                <button
                  onClick={() => setRefineModalOpen(false)}
                  className="flex-1 px-4 py-2 border border-ink-line text-ink-soft rounded-none hover:bg-paper-warm transition-colors"
                  disabled={refining}
                >
                  Annuler
                </button>
                <button
                  onClick={refineTask}
                  disabled={refining || !refinePrompt.trim()}
                  className="flex-1 px-4 py-2 bg-accent text-white rounded-none hover:bg-accent-deep transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {refining ? (
                    <>
                      <Loader size="lg" />
                      Raffinement en cours...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      Raffiner avec l'IA
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

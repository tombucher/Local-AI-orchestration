/**
 * Composant d'affichage du chemin critique avec tâches marquées
 */

import { useState, useEffect } from 'react';
import { Flame, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { tasksService } from '../../services/tasks';
import api from '../../services/api';
import type { Task } from '../../types/task.types';
import Loader from '../ui/Loader';

interface CriticalPathViewProps {
  projectId: number;
}

export const CriticalPathView = ({ projectId }: CriticalPathViewProps) => {
  const [criticalPathData, setCriticalPathData] = useState<any>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchCriticalPath = async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch critical path data
        const response = await api.get(`/projects/${projectId}/critical-path`);
        setCriticalPathData(response.data);

        // Fetch all tasks for the project
        const tasksData = await tasksService.getTasks({ project_id: projectId });
        setTasks(tasksData);

      } catch (err) {
        console.error('Error fetching critical path:', err);
        setError('Erreur lors du chargement du chemin critique');
      } finally {
        setLoading(false);
      }
    };

    fetchCriticalPath();
  }, [projectId]);

  if (loading) {
    return (
      <div className="bg-paper-card rounded-none shadow-card border border-ink-line p-6">
        <h2 className="text-lg font-semibold text-ink mb-4">Chemin Critique</h2>
        <div className="text-center py-8">
          <Loader size="lg" />
          <p className="text-sm text-ink-faint mt-2">Chargement du chemin critique...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-paper-card rounded-none shadow-card border border-ink-line p-6">
        <h2 className="text-lg font-semibold text-ink mb-4">Chemin Critique</h2>
        <div className="text-center py-8 text-danger">
          <AlertTriangle className="w-8 h-8 mx-auto mb-2" />
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!criticalPathData || criticalPathData.ordered_tasks.length === 0) {
    return (
      <div className="bg-paper-card rounded-none shadow-card border border-ink-line p-6">
        <h2 className="text-lg font-semibold text-ink mb-4">Chemin Critique</h2>
        <div className="text-center py-8 text-ink-faint">
          <p>Aucun chemin critique disponible pour ce projet</p>
        </div>
      </div>
    );
  }

  // Create a map of task IDs to task objects for quick lookup
  const taskMap = new Map(tasks.map(task => [task.id, task]));

  return (
    <div className="bg-paper-card rounded-none shadow-card border border-ink-line p-6">
      <h2 className="text-lg font-semibold text-ink mb-4">Chemin Critique</h2>

      {/* Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        <div className="p-3 bg-info/5 rounded-none">
          <p className="text-sm text-accent mb-1">Tâches totales</p>
          <p className="text-xl font-bold text-info">{criticalPathData.ordered_tasks.length}</p>
        </div>
        <div className="p-3 bg-danger/5 rounded-none">
          <p className="text-sm text-danger mb-1">Tâches critiques</p>
          <p className="text-xl font-bold text-danger">{criticalPathData.critical_tasks.length}</p>
        </div>
        <div className="p-3 bg-success/5 rounded-none">
          <p className="text-sm text-success mb-1">Durée totale</p>
          <p className="text-xl font-bold text-success">{criticalPathData.total_duration} jours</p>
        </div>
        <div className="p-3 bg-warning/5 rounded-none">
          <p className="text-sm text-warning mb-1">Cycle détecté</p>
          <p className="text-xl font-bold text-warning">{criticalPathData.has_cycle ? 'Oui' : 'Non'}</p>
        </div>
      </div>

      {/* Tasks list */}
      <div className="space-y-4">
        {criticalPathData.ordered_tasks.map((taskData: any) => {
          const task = taskMap.get(taskData.task_id);
          const isCritical = taskData.is_critical;

          return (
            <div
              key={taskData.task_id}
              className={`border border-ink-line rounded-none p-4 transition-all ${
                isCritical ? 'border-danger/50 bg-danger/5' : 'hover:border-primary'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="font-medium text-ink">{task?.title || `Tâche #${taskData.task_id}`}</h3>
                    {isCritical && (
                      <span className="flex items-center gap-1 px-2 py-1 bg-danger/10 text-danger text-xs font-medium rounded-full">
                        <Flame className="w-3 h-3" />
                        Critique
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-ink-soft">Début au plus tôt</p>
                      <p className="font-medium text-ink">Jour {taskData.early_start}</p>
                    </div>
                    <div>
                      <p className="text-ink-soft">Fin au plus tôt</p>
                      <p className="font-medium text-ink">Jour {taskData.early_finish}</p>
                    </div>
                    <div>
                      <p className="text-ink-soft">Début au plus tard</p>
                      <p className="font-medium text-ink">Jour {taskData.late_start}</p>
                    </div>
                    <div>
                      <p className="text-ink-soft">Fin au plus tard</p>
                      <p className="font-medium text-ink">Jour {taskData.late_finish}</p>
                    </div>
                  </div>

                  <div className="mt-3 text-sm">
                    <p className="text-ink-soft">Marge</p>
                    <p className={`font-medium ${taskData.slack === 0 ? 'text-danger' : 'text-success'}`}>
                      {taskData.slack} jours {taskData.slack === 0 ? '(Aucune marge)' : '(Marge disponible)'}
                    </p>
                  </div>
                </div>

                {task && (
                  <div className="ml-4 flex-shrink-0">
                    <CheckCircle2 className={`w-6 h-6 ${task.status === 'completed' ? 'text-success' : 'text-ink-line'}`} />
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Warning for cycles */}
      {criticalPathData.has_cycle && (
        <div className="mt-6 p-4 bg-warning/5 border border-warning/30 rounded-none">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-warning mt-0.5" />
            <div>
              <p className="font-medium text-warning">⚠️ Cycle détecté dans les dépendances</p>
              <p className="text-sm text-warning mt-1">
                Un cycle a été détecté dans les dépendances entre tâches, ce qui empêche le calcul précis du chemin critique.
                Veuillez revoir les dépendances de vos tâches pour résoudre ce problème.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
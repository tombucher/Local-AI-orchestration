/**
 * Liste des tâches d'un projet, enrichie des données de chemin critique,
 * avec sous-tâches dépliables (checklist extraite de la description).
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronDown, ChevronUp, Flame, Square } from 'lucide-react';
import type { Task } from '../../types/task.types';
import type { CriticalPathTaskData } from '../../types/critical-path.types';
import { TaskTypeBadge } from '../tasks/TaskTypeBadge';
import { StatusBadge } from '../tasks/StatusBadge';
import { PriorityBadge } from '../tasks/PriorityBadge';
import Loader from '../ui/Loader';

interface ProjectTasksBoardProps {
  projectId: number;
  tasks: Task[];
  loading: boolean;
  criticalPathMap: Map<number, CriticalPathTaskData>;
}

/** Sépare la description de la checklist « **Checklist:** - [ ] … » générée par l'analyse IA */
const extractSubtasks = (description: string): { description: string; subtasks: string[] } => {
  if (!description) return { description: '', subtasks: [] };
  const match = description.match(/\*\*Checklist:\*\*([\s\S]*)/);
  if (!match) return { description, subtasks: [] };
  const subtasks = match[1]
    .split('\n')
    .filter((line) => line.trim().startsWith('- ['))
    .map((line) => line.replace(/^-\s*\[(x| )\]\s*/, '').trim());
  return { description: description.substring(0, match.index).trim(), subtasks };
};

const hoursFromUnits = (units: number) => Math.round(units / 3600);

export const ProjectTasksBoard = ({ projectId, tasks, loading, criticalPathMap }: ProjectTasksBoardProps) => {
  const navigate = useNavigate();
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const toggle = (taskId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(taskId) ? next.delete(taskId) : next.add(taskId);
      return next;
    });
  };

  const newTaskUrl = `/tasks/new?project_id=${projectId}`;

  return (
    <div className="bg-paper-card shadow-card border border-ink-line p-6">
      <div className="flex items-center justify-between mb-4 pb-2 rule">
        <h2 className="font-display text-2xl text-ink">Tâches</h2>
        <button
          onClick={() => navigate(newTaskUrl)}
          className="px-3 py-1.5 bg-accent text-white hover:bg-accent-deep transition-colors text-xs font-semibold uppercase tracking-wide"
        >
          + Nouvelle tâche
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-8"><Loader size="lg" label="Chargement des tâches…" /></div>
      ) : tasks.length === 0 ? (
        <div className="text-center py-12 border border-dashed border-ink-line">
          <p className="text-ink-faint">Aucune tâche pour ce projet</p>
          <button onClick={() => navigate(newTaskUrl)} className="mt-4 text-accent hover:underline">
            Créer la première tâche
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {tasks.map((task) => {
            const { description, subtasks } = extractSubtasks(task.description || '');
            const cp = criticalPathMap.get(task.id);
            const isCritical = cp?.is_critical ?? false;

            return (
              <div
                key={task.id}
                onClick={() => navigate(`/tasks/${task.id}`)}
                className={`border p-4 transition-all cursor-pointer hover:shadow-card ${
                  isCritical ? 'border-ink-line border-l-2 border-l-accent' : 'border-ink-line hover:border-ink'
                }`}
              >
                <div className="flex items-center gap-2 mb-2 flex-wrap">
                  <h3 className="font-medium text-ink">{task.title}</h3>
                  {isCritical && (
                    <span className="flex items-center gap-1 kicker text-accent">
                      <Flame className="w-3 h-3" />
                      Critique
                    </span>
                  )}
                  <TaskTypeBadge taskType={task.task_type} />
                  <PriorityBadge priority={task.priority} size="sm" />
                  <StatusBadge status={task.status} size="sm" />
                  {task.estimated_duration && (
                    <span className="text-xs text-ink-faint figures">~{hoursFromUnits(task.estimated_duration)} h</span>
                  )}
                </div>

                {description && <p className="text-sm text-ink-soft mb-2">{description}</p>}

                {cp && (
                  <div className="flex items-center gap-4 text-xs mb-2 figures">
                    <span className="text-ink-faint">
                      Début : <span className="font-medium text-ink-soft">
                        {new Date(cp.projected_start).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })}
                      </span>
                    </span>
                    <span className="text-ink-faint">
                      Fin : <span className="font-medium text-ink-soft">
                        {new Date(cp.projected_end).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })}
                      </span>
                    </span>
                    <span className={`font-medium ${cp.slack === 0 ? 'text-accent' : 'text-success'}`}>
                      Marge : {cp.slack === 0 ? 'aucune' : `${hoursFromUnits(cp.slack)} h`}
                    </span>
                  </div>
                )}

                {subtasks.length > 0 && (
                  <div>
                    <button onClick={(e) => toggle(task.id, e)} className="flex items-center gap-1 text-xs text-ink-faint hover:text-ink-soft mt-1">
                      {expanded.has(task.id) ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                      {subtasks.length} sous-tâche{subtasks.length > 1 ? 's' : ''}
                    </button>
                    {expanded.has(task.id) && (
                      <div className="mt-2 space-y-1 ml-4">
                        {subtasks.map((sub, i) => (
                          <div key={i} className="flex items-start gap-2 text-sm">
                            <Square className="w-4 h-4 text-ink-faint mt-0.5 shrink-0" />
                            <span className="text-ink-soft">{sub}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

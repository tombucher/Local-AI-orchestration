/**
 * Liste des tâches d'un projet, enrichie des données de chemin critique,
 * avec sous-tâches dépliables (checklist extraite de la description).
 */

import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronDown, ChevronUp, Flame, Lock, Square } from 'lucide-react';
import type { Task } from '../../types/task.types';
import { TaskStatus } from '../../types/task.types';
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
  /** Ordre d'exécution conseillé (tri topologique du chemin critique) : id → rang */
  taskOrder?: Map<number, number>;
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

const TERMINEES = new Set<string>([TaskStatus.COMPLETED, TaskStatus.CANCELLED]);

export const ProjectTasksBoard = ({ projectId, tasks, loading, criticalPathMap, taskOrder }: ProjectTasksBoardProps) => {
  const navigate = useNavigate();
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  // Ordre conseillé : le backend fournit un tri topologique (chemin critique) qui
  // respecte les dépendances. Sans lui, la liste arrivait dans l'ordre de création,
  // donc « en vrac » — rien n'indiquait par quoi commencer.
  const ordered = useMemo(() => {
    const rang = (t: Task) => taskOrder?.get(t.id) ?? Number.MAX_SAFE_INTEGER;
    return [...tasks].sort((a, b) => rang(a) - rang(b) || a.id - b.id);
  }, [tasks, taskOrder]);

  const statuts = useMemo(() => new Map(tasks.map((t) => [t.id, t.status as string])), [tasks]);

  /** Dépendances non terminées d'une tâche — elle ne devrait pas démarrer avant */
  const bloquantes = (task: Task): Task[] =>
    (criticalPathMap.get(task.id)?.depends_on ?? [])
      .filter((id) => !TERMINEES.has(statuts.get(id) ?? ''))
      .map((id) => tasks.find((t) => t.id === id))
      .filter((t): t is Task => Boolean(t));

  // Première tâche réellement attaquable : ni terminée, ni bloquée
  const prochaine = ordered.find(
    (t) => !TERMINEES.has(t.status as string) && bloquantes(t).length === 0,
  );

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
        <div>
          <h2 className="font-display text-2xl text-ink">Tâches</h2>
          {taskOrder && taskOrder.size > 0 && (
            <p className="text-xs text-ink-faint mt-0.5">
              Classées dans l'ordre conseillé, dépendances respectées
            </p>
          )}
        </div>
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
          {ordered.map((task, position) => {
            const { description, subtasks } = extractSubtasks(task.description || '');
            const cp = criticalPathMap.get(task.id);
            const isCritical = cp?.is_critical ?? false;
            const attente = bloquantes(task);
            const estProchaine = prochaine?.id === task.id;
            const terminee = TERMINEES.has(task.status as string);

            return (
              <div
                key={task.id}
                onClick={() => navigate(`/tasks/${task.id}`)}
                className={`border p-4 transition-all cursor-pointer hover:shadow-card ${
                  isCritical ? 'border-ink-line border-l-2 border-l-accent' : 'border-ink-line hover:border-ink'
                }`}
              >
                <div className="flex items-center gap-2 mb-2 flex-wrap">
                  {/* Rang dans l'ordre conseillé : l'information manquait totalement */}
                  <span
                    className={`shrink-0 w-6 h-6 flex items-center justify-center text-xs font-mono figures border ${
                      terminee
                        ? 'border-ink-line text-ink-faint line-through'
                        : estProchaine
                          ? 'border-accent bg-accent text-paper'
                          : 'border-ink-line text-ink-soft'
                    }`}
                    title={`Étape ${position + 1} de l'ordre conseillé`}
                  >
                    {position + 1}
                  </span>
                  <h3 className={`font-medium ${terminee ? 'text-ink-faint line-through' : 'text-ink'}`}>
                    {task.title}
                  </h3>
                  {estProchaine && (
                    <span className="kicker text-accent">À faire maintenant</span>
                  )}
                  {attente.length > 0 && (
                    <span className="flex items-center gap-1 kicker text-warning" title={attente.map((t) => t.title).join(' · ')}>
                      <Lock className="w-3 h-3" />
                      Bloquée
                    </span>
                  )}
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

                {attente.length > 0 && (
                  <p className="text-xs text-warning mb-2">
                    À terminer d'abord : {attente.map((t) => `« ${t.title} »`).join(', ')}
                  </p>
                )}

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

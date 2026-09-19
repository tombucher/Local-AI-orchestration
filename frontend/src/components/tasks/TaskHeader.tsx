/**
 * En-tête de la page tâche : titre, badges, description, actions (chrono, éditer, supprimer).
 */

import { Edit, Play, Trash2 } from 'lucide-react';
import type { Task } from '../../types/task.types';
import { StatusBadge } from './StatusBadge';
import { PriorityBadge } from './PriorityBadge';
import { getTaskTypeIcon, getTaskTypeLabel } from './taskTypeUtils';

interface TaskHeaderProps {
  task: Task;
  canStartTimer: boolean;
  onStartTimer: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

export const TaskHeader = ({ task, canStartTimer, onStartTimer, onEdit, onDelete }: TaskHeaderProps) => (
  <div className="bg-paper-card shadow-card border border-ink-line p-6 mb-6">
    <div className="flex items-start justify-between gap-4 mb-4">
      <div className="flex-1 min-w-0">
        <h1 className="font-display text-3xl text-ink mb-3">{task.title}</h1>
        <div className="flex flex-wrap gap-2">
          <StatusBadge status={task.status} />
          <PriorityBadge priority={task.priority} />
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 border border-ink-line bg-paper-card text-xs font-semibold uppercase tracking-[0.08em] text-ink-soft">
            {getTaskTypeIcon(task.task_type)}
            {getTaskTypeLabel(task.task_type)}
          </span>
        </div>
      </div>
      <div className="flex gap-2 shrink-0">
        {canStartTimer && (
          <button
            onClick={onStartTimer}
            className="flex items-center gap-2 px-4 py-2 text-success bg-success/5 border border-success/30 hover:bg-success/15 transition-colors"
          >
            <Play className="w-4 h-4" />
            Chrono
          </button>
        )}
        <button
          onClick={onEdit}
          className="flex items-center gap-2 px-4 py-2 text-ink-soft bg-paper-warm hover:text-ink transition-colors"
        >
          <Edit className="w-4 h-4" />
          Éditer
        </button>
        <button
          onClick={onDelete}
          className="flex items-center gap-2 px-4 py-2 text-white bg-danger hover:opacity-90 transition-colors"
        >
          <Trash2 className="w-4 h-4" />
          Supprimer
        </button>
      </div>
    </div>

    {task.description && <p className="text-ink-soft mt-4">{task.description}</p>}
  </div>
);

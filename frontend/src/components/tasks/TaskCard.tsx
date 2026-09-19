/**
 * Carte pour afficher une tâche dans la liste
 */

import { Task, TaskStatus } from '../../types/task.types';
import { StatusBadge } from './StatusBadge';
import { PriorityBadge } from './PriorityBadge';
import { TaskTypeBadge } from './TaskTypeBadge';
import { Clock, Calendar, Folder, AlertCircle } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { fr } from 'date-fns/locale';

interface TaskCardProps {
  task: Task;
  onClick: (id: number) => void;
}

export const TaskCard = ({ task, onClick }: TaskCardProps) => {
  const truncateText = (text: string | null, maxLength = 100) => {
    if (!text) return 'Aucune description';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  return (
    <div
      onClick={() => onClick(task.id)}
      className="bg-paper-card rounded-none shadow-card border border-ink-line p-4 hover:shadow-md hover:border-primary transition-all cursor-pointer"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-base font-semibold text-ink truncate">
            {task.title}
          </h3>
          {/* Nom du projet */}
          {task.project_name && (
            <div className="flex items-center gap-1 mt-1 text-xs text-ink-faint">
              <Folder className="w-3 h-3" />
              <span>{task.project_name}</span>
            </div>
          )}
        </div>
        <div className="ml-2 flex-shrink-0">
          <PriorityBadge priority={task.priority} size="sm" />
        </div>
      </div>

      {/* Description */}
      <p className="text-sm text-ink-soft mb-3 line-clamp-2">
        {truncateText(task.description)}
      </p>

      {/* Status and Type */}
      <div className="mb-3 flex items-center gap-2 flex-wrap">
        <StatusBadge status={task.status} size="sm" />
        <TaskTypeBadge taskType={task.task_type} />
        {task.status === TaskStatus.MANUAL_REVIEW && (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-semibold bg-highlight/30 text-ink border border-highlight animate-pulse">
            <AlertCircle className="w-3 h-3" />
            Action requise
          </span>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-ink-faint">
        <div className="flex items-center gap-1">
          <Calendar className="w-3 h-3" />
          <span>
            {formatDistanceToNow(new Date(task.created_at), {
              addSuffix: true,
              locale: fr,
            })}
          </span>
        </div>

        {task.estimated_duration && (
          <div className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            <span>{task.estimated_duration}h estimé</span>
          </div>
        )}
      </div>
    </div>
  );
};

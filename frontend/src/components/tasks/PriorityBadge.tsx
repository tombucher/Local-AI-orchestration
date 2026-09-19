/**
 * Badge de priorité — étiquette éditoriale. P1 est le seul badge plein
 * (l'urgence mérite l'encre), P2/P3 restent en filet.
 */

import { TaskPriority } from '../../types/task.types';

interface PriorityBadgeProps {
  priority: TaskPriority;
  size?: 'sm' | 'md' | 'lg';
}

const priorityConfig: Record<TaskPriority, { label: string; className: string }> = {
  [TaskPriority.P1]: {
    label: 'P1 · Urgent',
    className: 'bg-accent border-accent text-white',
  },
  [TaskPriority.P2]: {
    label: 'P2 · Important',
    className: 'bg-paper-card border-ink text-ink',
  },
  [TaskPriority.P3]: {
    label: 'P3 · Normal',
    className: 'bg-paper-card border-ink-line text-ink-faint',
  },
};

const sizeClasses = {
  sm: 'text-[10px] px-2 py-0.5',
  md: 'text-xs px-2.5 py-1',
  lg: 'text-sm px-3 py-1.5',
};

export const PriorityBadge = ({ priority, size = 'md' }: PriorityBadgeProps) => {
  const config = priorityConfig[priority];

  return (
    <span
      className={`inline-flex items-center border font-semibold uppercase tracking-[0.08em]
        ${config.className} ${sizeClasses[size]}`}
    >
      {config.label}
    </span>
  );
};

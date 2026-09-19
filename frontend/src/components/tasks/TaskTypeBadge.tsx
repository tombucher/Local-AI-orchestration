/**
 * Badge pour afficher le type de tâche avec icône et couleur
 */

import { TaskType } from '../../types/task.types';

interface TaskTypeBadgeProps {
  taskType: TaskType;
  className?: string;
}

const taskTypeConfig = {
  [TaskType.CODE_GENERATION]: {
    icon: '💻',
    label: 'Code',
    color: 'bg-info/10 text-info',
  },
  [TaskType.DOCUMENT_WRITING]: {
    icon: '📄',
    label: 'Document',
    color: 'bg-accent-wash text-accent-deep',
  },
  [TaskType.FUNDING_SEARCH]: {
    icon: '💰',
    label: 'Financement',
    color: 'bg-success/10 text-success',
  },
  [TaskType.VEILLE]: {
    icon: '🔍',
    label: 'Veille',
    color: 'bg-accent-wash text-accent-deep',
  },
  [TaskType.VEILLE_TECH]: {
    icon: '🔍',
    label: 'Veille',
    color: 'bg-accent-wash text-accent-deep',
  },
  [TaskType.VEILLE_CULTURAL]: {
    icon: '🔍',
    label: 'Veille',
    color: 'bg-accent-wash text-accent-deep',
  },
  [TaskType.VEILLE_EVENTS]: {
    icon: '🔍',
    label: 'Veille',
    color: 'bg-accent-wash text-accent-deep',
  },
  [TaskType.ADMINISTRATIVE]: {
    icon: '📋',
    label: 'Admin',
    color: 'bg-paper-warm text-ink',
  },
  [TaskType.RESEARCH]: {
    icon: '🔬',
    label: 'Recherche',
    color: 'bg-success/10 text-success',
  },
};

export const TaskTypeBadge = ({ taskType, className = '' }: TaskTypeBadgeProps) => {
  const config = taskTypeConfig[taskType] || taskTypeConfig[TaskType.CODE_GENERATION];

  return (
    <span
      className={`inline-flex items-center border border-ink-line bg-paper-card uppercase tracking-[0.08em] gap-1 px-2 py-1  text-xs font-medium ${config.color} ${className}`}
    >
      <span>{config.icon}</span>
      <span>{config.label}</span>
    </span>
  );
};

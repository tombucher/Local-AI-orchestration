/**
 * Badge de statut — étiquette éditoriale : petites capitales, filet coloré,
 * point d'état. Cohérent avec components/Badge.tsx.
 */

import { TaskStatus } from '../../types/task.types';

interface StatusBadgeProps {
  status: TaskStatus;
  size?: 'sm' | 'md' | 'lg';
}

const statusConfig: Record<TaskStatus, { label: string; className: string; dot: string; pulse?: boolean }> = {
  [TaskStatus.CREATED]: {
    label: 'Créée',
    className: 'border-ink-line text-ink-faint',
    dot: 'bg-ink-faint',
  },
  [TaskStatus.READY]: {
    label: 'Prête',
    className: 'border-info text-info',
    dot: 'bg-info',
  },
  [TaskStatus.GENERATING]: {
    label: 'Génération…',
    className: 'border-warning text-warning',
    dot: 'bg-warning',
    pulse: true,
  },
  [TaskStatus.MANUAL_REVIEW]: {
    label: 'À valider',
    className: 'border-highlight text-ink bg-highlight/20',
    dot: 'bg-ink',
    pulse: true,
  },
  [TaskStatus.COMPLETED]: {
    label: 'Terminée',
    className: 'border-success text-success',
    dot: 'bg-success',
  },
  [TaskStatus.FAILED]: {
    label: 'Échec',
    className: 'border-danger text-danger',
    dot: 'bg-danger',
  },
  [TaskStatus.CANCELLED]: {
    label: 'Annulée',
    className: 'border-ink-line text-ink-faint line-through',
    dot: 'bg-ink-line',
  },
};

const sizeClasses = {
  sm: 'text-[10px] px-2 py-0.5 gap-1.5',
  md: 'text-xs px-2.5 py-1 gap-2',
  lg: 'text-sm px-3 py-1.5 gap-2',
};

export const StatusBadge = ({ status, size = 'md' }: StatusBadgeProps) => {
  const config = statusConfig[status];

  return (
    <span
      className={`inline-flex items-center border bg-paper-card font-semibold uppercase tracking-[0.08em]
        ${config.className} ${sizeClasses[size]}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${config.dot} ${config.pulse ? 'animate-pulse' : ''}`} />
      {config.label}
    </span>
  );
};

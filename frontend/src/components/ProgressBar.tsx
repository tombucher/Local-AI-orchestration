/**
 * Barre de progression — trait plein encre/vermillon sur fond papier chaud.
 */

interface ProgressBarProps {
  current: number;
  total: number;
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
  color?: string;
}

const sizeStyles = {
  sm: 'h-1',
  md: 'h-1.5',
  lg: 'h-2.5',
};

export const ProgressBar = ({
  current,
  total,
  showLabel = true,
  size = 'md',
  color = 'bg-accent',
}: ProgressBarProps) => {
  const percentage = total > 0 ? Math.round((current / total) * 100) : 0;

  return (
    <div className="w-full">
      {showLabel && (
        <div className="flex justify-between items-center mb-1">
          <span className="text-xs text-ink-faint figures">
            {current} / {total}
          </span>
          <span className="text-xs font-semibold text-ink figures">{percentage}%</span>
        </div>
      )}
      <div className={`w-full bg-paper-warm border border-ink-line/60 overflow-hidden ${sizeStyles[size]}`}>
        <div
          className={`${color === 'bg-primary' ? 'bg-accent' : color} h-full transition-all duration-500`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};

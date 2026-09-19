/**
 * Composant d'affichage du score de maturité avec jauge visuelle
 */

import { Gauge } from 'lucide-react';

interface MaturityScoreProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
}

const sizeStyles = {
  sm: { gaugeSize: 120, textSize: 'text-lg' },
  md: { gaugeSize: 160, textSize: 'text-xl' },
  lg: { gaugeSize: 200, textSize: 'text-2xl' },
};

export const MaturityScore = ({ score, size = 'md' }: MaturityScoreProps) => {
  const { gaugeSize, textSize } = sizeStyles[size];

  // Calculer la couleur en fonction du score
  const getScoreColor = () => {
    if (score >= 80) return 'text-success';
    if (score >= 60) return 'text-warning';
    if (score >= 40) return 'text-warning';
    return 'text-danger';
  };

  // Calculer la position de l'aiguille (0-180 degrés pour un demi-cercle)
  const needleRotation = (score / 100) * 180;

  return (
    <div className="flex flex-col items-center justify-center">
      <div className="relative" style={{ width: gaugeSize, height: gaugeSize / 2 }}>
        {/* Cercle de fond */}
        <div className="absolute inset-0">
          <svg width="100%" height="100%" viewBox="0 0 160 80">
            <path
              d="M20,80 A60,60 0 0,1 140,80"
              fill="none"
              stroke="#e5e7eb"
              strokeWidth="12"
              strokeLinecap="round"
            />
          </svg>
        </div>

        {/* Arc de progression */}
        <div className="absolute inset-0">
          <svg width="100%" height="100%" viewBox="0 0 160 80">
            <path
              d="M20,80 A60,60 0 0,1 140,80"
              fill="none"
              stroke="#3b82f6"  // blue-500
              strokeWidth="12"
              strokeLinecap="round"
              strokeDasharray={`${(score / 100) * 180}, 180`}
              strokeDashoffset="0"
              style={{
                strokeDasharray: `${(score / 100) * 180}, 180`,
                transition: 'stroke-dasharray 0.5s ease-in-out'
              }}
            />
          </svg>
        </div>

        {/* Aiguille */}
        <div
          className="absolute inset-0 flex items-center justify-center"
          style={{
            transform: `rotate(${needleRotation - 90}deg)`,
            transformOrigin: 'center bottom',
            transition: 'transform 0.5s ease-in-out'
          }}
        >
          <div className="w-1 h-20 bg-ink rounded-full" style={{ transformOrigin: 'center bottom' }} />
          <div className="w-4 h-4 bg-ink rounded-full -mt-2" />
        </div>
      </div>

      {/* Score */}
      <div className={`mt-4 ${textSize} font-bold ${getScoreColor()}`}>
        {score}/100
      </div>

      {/* Légende */}
      <div className="mt-2 text-sm text-ink-soft flex items-center gap-1">
        <Gauge className="w-4 h-4" />
        Score de maturité
      </div>

      {/* Indicateur de qualité */}
      <div className="mt-1 text-xs">
        <span className={`px-2 py-1 rounded-full ${getScoreColor().replace('text', 'bg')} text-white`}>
          {score >= 80 ? 'Excellent' : score >= 60 ? 'Bon' : score >= 40 ? 'Moyen' : 'À améliorer'}
        </span>
      </div>
    </div>
  );
};
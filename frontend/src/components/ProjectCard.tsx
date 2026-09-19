/**
 * Carte projet pour affichage en grid
 */

import { Code, Eye, GitBranch } from 'lucide-react';
import { Project } from '../types/project.types';
import { Badge } from './Badge';
import { ProgressBar } from './ProgressBar';

interface ProjectCardProps {
  project: Project;
  onView: (id: number) => void;
}

const getTypeLabel = (type: string): string => {
  const labels: Record<string, string> = {
    professional: 'Professionnel',
    personal: 'Personnel',
    research: 'Recherche',
  };
  return labels[type] || type;
};

export const ProjectCard = ({ project, onView }: ProjectCardProps) => {
  // Utiliser les statistiques si disponibles, sinon 0
  const tasksCompleted = project.tasks_completed ?? 0;
  const tasksTotal = project.tasks_total ?? 0;

  const truncateDescription = (text?: string | null, maxLength = 100) => {
    if (!text) return 'Aucune description';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  return (
    <div
      onClick={() => onView(project.id)}
      className="bg-paper-card border border-ink-line shadow-card p-5 hover:shadow-lifted hover:-translate-y-0.5 transition-all duration-200 cursor-pointer group"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h3 className="font-display text-xl text-ink mb-2 leading-snug group-hover:text-accent transition-colors">{project.name}</h3>
          <div className="flex gap-2">
            <Badge label={getTypeLabel(project.type)} variant={project.type} />
          </div>
        </div>
      </div>

      {/* Description */}
      <p className="text-sm text-ink-soft mb-4 line-clamp-2">
        {truncateDescription(project.description)}
      </p>

      {/* Features */}
      {project.features && (
        <div className="flex gap-3 mb-4">
          {project.features.code_gen && (
            <div className="flex items-center gap-1 text-ink-faint" title="Génération de code">
              <Code className="w-4 h-4" />
            </div>
          )}
          {project.features.veille && (
            <div className="flex items-center gap-1 text-ink-faint" title="Veille">
              <Eye className="w-4 h-4" />
            </div>
          )}
          {project.features.git_auto && (
            <div className="flex items-center gap-1 text-ink-faint" title="Git automatique">
              <GitBranch className="w-4 h-4" />
            </div>
          )}
        </div>
      )}

      {/* Progression */}
      <div className="mb-4">
        <ProgressBar current={tasksCompleted} total={tasksTotal} size="sm" />
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between text-[11px] text-ink-faint figures pt-3 border-t border-ink-line">
        <span>Créé le {new Date(project.created_at).toLocaleDateString('fr-FR')}</span>
        {project.financial_config?.budget && (
          <span className="font-medium text-ink-soft">
            Budget : {project.financial_config.budget} €
          </span>
        )}
      </div>
    </div>
  );
};

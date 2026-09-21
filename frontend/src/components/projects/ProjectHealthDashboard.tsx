/**
 * Santé du projet : score et indicateurs de maturité, statistiques des tâches,
 * résumé du chemin critique et frise Gantt.
 */

import { AlertTriangle, Flame } from 'lucide-react';
import type { Project, ProjectStats } from '../../types/project.types';
import type { CriticalPathData } from '../../types/critical-path.types';
import { MaturityScore } from './MaturityScore';
import { MaturityIndicators } from './MaturityIndicators';
import { AIAnalysisButton } from './AIAnalysisButton';
import { GanttChart } from './GanttChart';

interface ProjectHealthDashboardProps {
  project: Project;
  stats: ProjectStats | null;
  criticalPath: CriticalPathData | null;
  onResizeTask?: (taskId: number, seconds: number) => void;
  onLinkTasks?: (taskId: number, dependsOnId: number) => void;
}

const Stat = ({ label, value, tone = 'text-ink' }: { label: string; value: number | string; tone?: string }) => (
  <div className="p-4 bg-paper border border-ink-line">
    <p className="kicker mb-1">{label}</p>
    <p className={`font-display text-2xl figures ${tone}`}>{value}</p>
  </div>
);

export const ProjectHealthDashboard = ({ project, stats, criticalPath, onResizeTask, onLinkTasks }: ProjectHealthDashboardProps) => (
  <div className="mb-6">
    <h2 className="font-display text-2xl text-ink mb-4 pb-2 rule">Santé du projet</h2>

    {/* Maturité */}
    <div className="bg-paper-card shadow-card border border-ink-line p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-display text-xl text-ink">Maturité du plan</h3>
          {/* Le score note la QUALITÉ DU PLAN (dépendances, descriptions,
              échéances, chemin critique), pas ce qui a été réalisé. Sans cette
              précision il se lit comme un taux d'avancement. */}
          <p className="text-xs text-ink-faint mt-0.5">
            Qualité de l'organisation : dépendances, descriptions, échéances, chemin critique.
            Ne mesure pas ce qui a été produit.
          </p>
        </div>
        <AIAnalysisButton projectId={project.id} onAnalysisComplete={() => {}} />
      </div>
      <div className="flex flex-col items-center">
        <MaturityScore score={project.maturity_score || 0} size="lg" />
      </div>
    </div>
    <div className="mb-6">
      <MaturityIndicators projectId={project.id} maturityScore={project.maturity_score || 0} />
    </div>

    {/* Statistiques + chemin critique */}
    <div className="bg-paper-card shadow-card border border-ink-line p-6">
      <h3 className="font-display text-xl text-ink mb-4">Statistiques</h3>

      {stats ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
          <Stat label="Total" value={stats.total_tasks} />
          <Stat label="En attente" value={stats.tasks_pending ?? 0} tone="text-info" />
          <Stat label="En cours" value={stats.tasks_in_progress ?? 0} tone="text-warning" />
          <Stat label="Terminées" value={stats.tasks_completed ?? 0} tone="text-success" />
        </div>
      ) : (
        <p className="text-sm text-ink-faint mb-4">Chargement des statistiques…</p>
      )}

      {/* Ce qui existe vraiment : une tâche pouvait être « terminée » sans avoir
          produit la moindre ligne, et le projet paraissait alors abouti. */}
      {stats && (
        <div className="mb-4 p-4 bg-paper border border-ink-line flex items-baseline justify-between gap-4">
          <div>
            <p className="kicker mb-1">Avec un résultat réel</p>
            <p className="text-sm text-ink-soft">
              Tâches ayant produit un contenu, pas seulement marquées terminées
            </p>
          </div>
          <p className={`font-display text-2xl figures ${
            (stats.tasks_with_output ?? 0) < (stats.total_tasks ?? 0) ? 'text-warning' : 'text-success'
          }`}>
            {stats.tasks_with_output ?? 0}<span className="text-ink-faint"> / {stats.total_tasks}</span>
          </p>
        </div>
      )}

      {criticalPath && (
        <>
          <div className="grid grid-cols-3 gap-4">
            <div className="p-4 bg-paper border border-ink-line">
              <p className="kicker mb-1">Tâches critiques</p>
              <p className="font-display text-2xl text-danger figures flex items-center gap-2">
                <Flame className="w-5 h-5" />
                {criticalPath.critical_tasks.length}
              </p>
            </div>
            <Stat label="Charge estimée" value={`${Math.round(criticalPath.total_duration / 3600)} h`} tone="text-accent" />
            <Stat label="Cycle de dépendances" value={criticalPath.has_cycle ? 'Oui' : 'Non'} tone={criticalPath.has_cycle ? 'text-warning' : 'text-success'} />
          </div>

          {!criticalPath.has_cycle && criticalPath.ordered_tasks.length > 0 && (
            <div className="mt-6">
              <p className="kicker mb-3">Frise du projet</p>
              <GanttChart data={criticalPath} onResize={onResizeTask} onLink={onLinkTasks} />
            </div>
          )}

          {criticalPath.has_cycle && (
            <div className="mt-4 p-4 bg-warning/5 border border-warning/30 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-warning mt-0.5 shrink-0" />
              <div>
                <p className="font-medium text-warning">Cycle détecté dans les dépendances</p>
                <p className="text-sm text-ink-soft mt-1">
                  Revois les dépendances entre tâches pour permettre le calcul du chemin critique.
                </p>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  </div>
);

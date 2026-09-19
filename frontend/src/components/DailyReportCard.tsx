/**
 * Composant d'affichage du rapport quotidien sur le Dashboard
 */

import { DailyReport } from '../types/daily-report.types';
import { AlertCircle, CheckCircle, TrendingUp } from 'lucide-react';

interface DailyReportCardProps {
  report: DailyReport;
}

export const DailyReportCard = ({ report }: DailyReportCardProps) => {
  const getHealthColor = (health: string) => {
    switch (health) {
      case 'healthy':
        return 'text-success bg-success/5';
      case 'warning':
        return 'text-warning bg-warning/5';
      case 'critical':
        return 'text-danger bg-danger/5';
      default:
        return 'text-ink-soft bg-paper';
    }
  };

  const getHealthIcon = (health: string) => {
    switch (health) {
      case 'healthy':
        return <CheckCircle className="w-5 h-5" />;
      case 'warning':
      case 'critical':
        return <AlertCircle className="w-5 h-5" />;
      default:
        return <TrendingUp className="w-5 h-5" />;
    }
  };

  return (
    <div className="bg-paper-card rounded-none border border-ink-line p-6 space-y-6">
      {/* Header */}
      <div className="border-b border-ink-line pb-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-2xl">📊</span>
          <h2 className="text-xl font-bold text-ink">Rapport du Jour</h2>
        </div>
        <p className="text-sm text-ink-faint">
          {new Date(report.date).toLocaleDateString('fr-FR', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
          })}
        </p>
      </div>

      {/* Résumé */}
      <div>
        <p className="text-ink-soft">{report.summary}</p>
      </div>

      {/* Statistiques rapides */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="text-center p-3 bg-paper rounded-none">
          <div className="text-2xl font-bold text-ink">{report.active_projects}</div>
          <div className="text-xs text-ink-soft">Projets actifs</div>
        </div>
        <div className="text-center p-3 bg-paper rounded-none">
          <div className="text-2xl font-bold text-ink">{report.total_tasks}</div>
          <div className="text-xs text-ink-soft">Tâches totales</div>
        </div>
        <div className="text-center p-3 bg-success/5 rounded-none">
          <div className="text-2xl font-bold text-success">{report.completed_today}</div>
          <div className="text-xs text-ink-soft">Complétées aujourd'hui</div>
        </div>
        <div className="text-center p-3 bg-danger/5 rounded-none">
          <div className="text-2xl font-bold text-danger">{report.blockers_count}</div>
          <div className="text-xs text-ink-soft">Blocages</div>
        </div>
      </div>

      {/* Top 3 priorités */}
      {report.top_priorities && report.top_priorities.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-ink mb-3 flex items-center gap-2">
            🎯 Top 3 Priorités du Jour
          </h3>
          <ol className="space-y-2">
            {report.top_priorities.map((priority, index) => (
              <li key={index} className="flex items-start gap-2">
                <span className="font-bold text-primary">{index + 1}.</span>
                <span className="text-ink-soft">{priority}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Projets critiques */}
      {report.projects && report.projects.some((p) => p.health_status === 'critical') && (
        <div className="bg-danger/5 border border-danger/30 rounded-none p-4">
          <h3 className="text-sm font-semibold text-danger mb-2">
            ⚠️ Projets nécessitant attention
          </h3>
          <div className="space-y-2">
            {report.projects
              .filter((p) => p.health_status === 'critical')
              .map((project) => (
                <div key={project.project_id} className="text-sm">
                  <div className="font-medium text-danger">{project.project_name}</div>
                  <div className="text-danger">
                    {project.blockers.length} blocage(s) • {project.p1_tasks} tâche(s) P1
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Recommandations */}
      {report.recommendations && report.recommendations.length > 0 && (
        <div className="bg-info/5 border border-info/30 rounded-none p-4">
          <h3 className="text-sm font-semibold text-info mb-2">
            💡 Recommandations
          </h3>
          <ul className="space-y-1">
            {report.recommendations.map((recommendation, index) => (
              <li key={index} className="text-sm text-info">
                • {recommendation}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Santé des projets */}
      {report.projects && report.projects.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-ink mb-3">
            État des Projets
          </h3>
          <div className="space-y-2">
            {report.projects.map((project) => (
              <div
                key={project.project_id}
                className="flex items-center justify-between p-3 bg-paper rounded-none"
              >
                <div className="flex-1">
                  <div className="font-medium text-ink">{project.project_name}</div>
                  <div className="text-xs text-ink-soft">
                    {project.completed_tasks}/{project.total_tasks} tâches •{' '}
                    {project.completion_rate.toFixed(0)}% complété
                  </div>
                </div>
                <div
                  className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium ${getHealthColor(
                    project.health_status
                  )}`}
                >
                  {getHealthIcon(project.health_status)}
                  <span className="capitalize">{project.health_status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

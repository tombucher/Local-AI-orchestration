/**
 * Panneaux d'information du projet : fonctionnalités activées et configuration financière.
 */

import { Code, Eye, GitBranch } from 'lucide-react';
import type { Project } from '../../types/project.types';

const Feature = ({ active, icon, label }: { active: boolean; icon: React.ReactNode; label: string }) => (
  <div className={`flex items-center gap-3 p-4 border ${active ? 'border-ink bg-paper-card' : 'border-ink-line bg-paper opacity-60'}`}>
    <span className={active ? 'text-accent' : 'text-ink-faint'}>{icon}</span>
    <div>
      <p className="font-medium text-ink">{label}</p>
      <p className="text-xs text-ink-faint">{active ? 'Activé' : 'Désactivé'}</p>
    </div>
  </div>
);

export const ProjectFeaturesPanel = ({ project }: { project: Project }) => {
  if (!project.features) return null;
  return (
    <div className="bg-paper-card shadow-card border border-ink-line p-6 mb-6">
      <h2 className="font-display text-xl text-ink mb-4">Fonctionnalités</h2>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Feature active={!!project.features.code_gen} icon={<Code className="w-5 h-5" />} label="Génération de code" />
        <Feature active={!!project.features.veille} icon={<Eye className="w-5 h-5" />} label="Veille" />
        <Feature active={!!project.features.git_auto} icon={<GitBranch className="w-5 h-5" />} label="Git automatique" />
      </div>
    </div>
  );
};

export const ProjectFinancialPanel = ({ project }: { project: Project }) => {
  const fc = project.financial_config;
  if (!fc || (!fc.hourly_rate && !fc.budget)) return null;
  return (
    <div className="bg-paper-card shadow-card border border-ink-line p-6 mb-6">
      <h2 className="font-display text-xl text-ink mb-4">Configuration financière</h2>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {fc.hourly_rate && (
          <div>
            <p className="kicker mb-1">Taux horaire</p>
            <p className="font-display text-2xl text-ink figures">{fc.hourly_rate} €/h</p>
          </div>
        )}
        {fc.budget && (
          <div>
            <p className="kicker mb-1">Budget total</p>
            <p className="font-display text-2xl text-ink figures">{fc.budget} €</p>
          </div>
        )}
      </div>
    </div>
  );
};

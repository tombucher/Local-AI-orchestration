/**
 * États d'un projet du point de vue de l'utilisateur : actif, en pause, en
 * sommeil, archivé. IDEATION et PLANNING sont des projets actifs en
 * construction : ils se rangent avec les actifs.
 */

import { ProjectStatus, type Project } from '../types/project.types';

export type EtatProjet = 'actif' | 'pause' | 'sommeil' | 'archive';

export const etatDe = (project: Pick<Project, 'status'>): EtatProjet => {
  switch (project.status) {
    case ProjectStatus.PAUSED:
      return 'pause';
    case ProjectStatus.DORMANT:
      return 'sommeil';
    case ProjectStatus.ARCHIVED:
      return 'archive';
    default:
      return 'actif';
  }
};

/** « 15 novembre », « 1er décembre » à partir de « 2026-11-15 » */
export const dateLisible = (iso?: string | null) => {
  if (!iso) return '';
  const date = new Date(`${iso}T12:00:00`);
  const mois = date.toLocaleDateString('fr-FR', { month: 'long' });
  const jour = date.getDate();
  return `${jour === 1 ? '1er' : jour} ${mois}`;
};

/** Petit libellé d'état, ou null pour un projet actif */
export const libelleEtat = (project: Pick<Project, 'status' | 'resume_on'>): string | null => {
  switch (etatDe(project)) {
    case 'pause':
      return project.resume_on ? `En pause · reprise le ${dateLisible(project.resume_on)}` : 'En pause';
    case 'sommeil':
      return 'En sommeil';
    case 'archive':
      return 'Archivé';
    default:
      return null;
  }
};

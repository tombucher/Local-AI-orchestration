/**
 * Discuter d'un projet en cours avec l'IA, puis en tirer des tâches.
 *
 * L'idéation n'existait qu'à la création d'un projet : les projets venus des
 * fiches .md, souvent sans tâches, n'avaient aucun moyen d'en discuter. L'IA
 * démarre en connaissant la description et les tâches existantes ; « Proposer
 * des tâches » passe la discussion à l'analyse, où l'on choisit ce qu'on garde.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ListPlus, MessagesSquare } from 'lucide-react';
import { IdeationChat } from '../IdeationChat';
import { ideationService } from '../../services/ideation';

interface Props {
  projectId: number;
  sansTaches: boolean;
}

export const ProjectDiscussion = ({ projectId, sansTaches }: Props) => {
  const navigate = useNavigate();
  // Fermé par défaut : ouvrir la discussion lance le modèle local (lent, et il
  // bloque les autres tâches pendant ce temps) — pas à la simple visite de la page
  const [ouvert, setOuvert] = useState(false);
  const [envoi, setEnvoi] = useState(false);

  const proposerDesTaches = async () => {
    setEnvoi(true);
    try {
      await ideationService.saveTranscript(projectId);
      navigate(`/projects/${projectId}/analyze`);
    } catch {
      // l'intercepteur de l'API affiche déjà l'erreur
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <div className={`bg-paper-card shadow-card border p-6 mb-6 ${sansTaches ? 'border-accent' : 'border-ink-line'}`}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3 min-w-0">
          <MessagesSquare className="w-5 h-5 text-accent mt-1 shrink-0" />
          <div className="min-w-0">
            <h2 className="font-display text-xl text-ink">Discuter du projet avec l'IA</h2>
            <p className="text-sm text-ink-soft mt-1 max-w-2xl">
              {sansTaches
                ? "Ce projet n'a pas encore de tâches. Parles-en avec l'IA : elle connaît sa description, te pose des questions, puis te propose des tâches que tu choisis une à une."
                : "Pour préciser le projet, débloquer une étape ou trouver ce qui manque. L'IA connaît sa description et ses tâches ; elle peut ensuite t'en proposer de nouvelles."}
            </p>
          </div>
        </div>
        <button
          onClick={() => setOuvert((v) => !v)}
          className={`shrink-0 px-4 py-2 text-sm transition-colors ${
            sansTaches && !ouvert
              ? 'bg-accent text-white hover:opacity-90'
              : 'border border-ink-line text-ink hover:border-accent hover:text-accent'
          }`}
        >
          {ouvert ? 'Réduire' : 'Ouvrir la discussion'}
        </button>
      </div>

      {ouvert && (
        <div className="mt-4">
          <IdeationChat projectId={projectId} />
          <div className="mt-3 flex flex-wrap items-center justify-end gap-3">
            <p className="text-xs text-ink-faint">
              Les tâches proposées arrivent en attente : c'est toi qui les actives.
            </p>
            <button
              onClick={proposerDesTaches}
              disabled={envoi}
              className="inline-flex items-center gap-2 px-4 py-2 bg-accent text-white hover:opacity-90 disabled:opacity-40 text-sm font-medium"
            >
              <ListPlus className="w-4 h-4" />
              {envoi ? 'Préparation…' : 'Proposer des tâches à partir de la discussion'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProjectDiscussion;

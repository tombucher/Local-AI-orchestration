/**
 * Écrit la fiche .md d'un projet (et son dossier) d'après ce qui est dans l'outil.
 *
 * Sur demande seulement : l'outil ne réécrit jamais une fiche de lui-même. Si
 * la fiche a été retouchée depuis la dernière synchronisation, on demande
 * avant de l'écraser.
 */

import { useState } from 'react';
import axios from 'axios';
import { FileDown } from 'lucide-react';
import toast from 'react-hot-toast';
import { extractErrorMessage } from '../../services/api';
import { projectFoldersApi } from '../../services/projectFoldersApi';
import ConfirmDialog from '../ui/ConfirmDialog';

interface Props {
  projectId: number;
  hasFile: boolean;
  onWritten: () => void;
}

export const WriteMarkdownButton = ({ projectId, hasFile, onWritten }: Props) => {
  const [envoi, setEnvoi] = useState(false);
  const [conflit, setConflit] = useState<string | null>(null);

  const ecrire = async (force = false) => {
    setEnvoi(true);
    try {
      const r = await projectFoldersApi.writeProject(projectId, force);
      setConflit(null);
      toast.success(r.created ? `Fiche créée : ${r.display}` : 'Fiche mise à jour');
      onWritten();
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 412) {
        setConflit(extractErrorMessage(error));
      } else {
        toast.error(extractErrorMessage(error));
      }
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <>
      <button
        onClick={() => ecrire()}
        disabled={envoi}
        title="Écrit la fiche .md du projet dans ton dossier de projets, d'après ce qui est dans l'outil"
        className="flex items-center gap-2 px-4 py-2 text-ink border border-ink-line bg-paper-card hover:border-accent hover:text-accent disabled:opacity-40 transition-colors"
      >
        <FileDown className="w-4 h-4" />
        {envoi ? 'Écriture…' : hasFile ? 'Mettre à jour la fiche' : 'Écrire la fiche'}
      </button>
      <ConfirmDialog
        open={conflit !== null}
        title="Fiche modifiée à la main"
        message={`${conflit ?? ''} Elle sera relue par l'outil dans les 30 secondes : attends plutôt, puis relance. Ou remplace-la maintenant par la version de l'outil.`}
        confirmLabel="Remplacer la fiche"
        cancelLabel="Attendre"
        danger
        loading={envoi}
        onConfirm={() => ecrire(true)}
        onCancel={() => setConflit(null)}
      />
    </>
  );
};

export default WriteMarkdownButton;

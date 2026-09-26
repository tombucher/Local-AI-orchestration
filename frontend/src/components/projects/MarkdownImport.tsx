/**
 * Dépôt d'une fiche .md : bouton, ou glisser-déposer n'importe où sur la page.
 *
 * Avec un dossier de projets configuré, la fiche y est rangée dans un nouveau
 * dossier et reste synchronisée ; sinon le projet est simplement créé.
 */

import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText } from 'lucide-react';
import toast from 'react-hot-toast';
import { projectFoldersApi } from '../../services/projectFoldersApi';

const estUneFiche = (f: File) => /\.(md|markdown|txt)$/i.test(f.name);

export const MarkdownImport = () => {
  const navigate = useNavigate();
  const input = useRef<HTMLInputElement>(null);
  const [survol, setSurvol] = useState(false);
  const [envoi, setEnvoi] = useState(false);

  const importer = async (fichiers: File[]) => {
    const fiches = fichiers.filter(estUneFiche);
    if (!fiches.length) {
      toast.error('Dépose un fichier .md');
      return;
    }
    setEnvoi(true);
    try {
      let dernier: number | null = null;
      for (const fiche of fiches) {
        const projet = await projectFoldersApi.importMarkdown(fiche);
        dernier = projet.id;
        toast.success(
          projet.source_path
            ? `« ${projet.name} » créé, et rangé dans ton dossier de projets`
            : `« ${projet.name} » créé`,
        );
      }
      if (dernier && fiches.length === 1) navigate(`/projects/${dernier}`);
    } catch {
      // l'intercepteur de l'API affiche déjà l'erreur
    } finally {
      setEnvoi(false);
    }
  };

  // Glisser-déposer sur toute la page : on ne réagit qu'aux fichiers
  useEffect(() => {
    let profondeur = 0;
    const avecFichiers = (e: DragEvent) => Array.from(e.dataTransfer?.types ?? []).includes('Files');
    const entree = (e: DragEvent) => {
      if (!avecFichiers(e)) return;
      profondeur += 1;
      setSurvol(true);
    };
    const sortie = () => {
      profondeur = Math.max(0, profondeur - 1);
      if (profondeur === 0) setSurvol(false);
    };
    const dessus = (e: DragEvent) => {
      if (avecFichiers(e)) e.preventDefault();
    };
    const depot = (e: DragEvent) => {
      if (!avecFichiers(e)) return;
      e.preventDefault();
      profondeur = 0;
      setSurvol(false);
      importer(Array.from(e.dataTransfer?.files ?? []));
    };
    window.addEventListener('dragenter', entree);
    window.addEventListener('dragleave', sortie);
    window.addEventListener('dragover', dessus);
    window.addEventListener('drop', depot);
    return () => {
      window.removeEventListener('dragenter', entree);
      window.removeEventListener('dragleave', sortie);
      window.removeEventListener('dragover', dessus);
      window.removeEventListener('drop', depot);
    };
    // importer ne dépend que de navigate, stable
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <>
      <button
        onClick={() => input.current?.click()}
        disabled={envoi}
        title="Ou glisse un fichier .md n'importe où sur la page"
        className="flex items-center gap-2 px-4 py-2 border border-ink-line text-ink hover:border-accent hover:text-accent disabled:opacity-40 transition-colors font-medium"
      >
        <FileText className="w-5 h-5" />
        {envoi ? 'Import…' : 'Importer une fiche .md'}
      </button>
      <input
        ref={input}
        type="file"
        accept=".md,.markdown,.txt,text/markdown"
        multiple
        className="hidden"
        onChange={(e) => {
          importer(Array.from(e.target.files ?? []));
          e.target.value = '';
        }}
      />
      {survol && (
        <div className="fixed inset-0 z-50 bg-paper/90 border-4 border-dashed border-accent flex items-center justify-center pointer-events-none">
          <div className="text-center">
            <FileText className="w-12 h-12 text-accent mx-auto mb-3" />
            <p className="font-display text-2xl text-ink">Dépose ta fiche .md</p>
            <p className="text-sm text-ink-soft mt-1">Elle devient un projet</p>
          </div>
        </div>
      )}
    </>
  );
};

export default MarkdownImport;

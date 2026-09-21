/**
 * Espace documents du projet.
 *
 * Ce que l'orchestrateur ne peut pas deviner — une charte, un cahier des charges,
 * un extrait de code existant, une image de référence — se dépose ici. Les
 * documents sont ensuite injectés dans les prompts selon la tâche, avec un budget
 * de caractères, et les images ne partent qu'aux modèles dotés de vision.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Code2, FileText, Image as ImageIcon, Paperclip, Plus, Trash2, Upload } from 'lucide-react';
import toast from 'react-hot-toast';
import { documentsApi } from '../../services/documentsApi';
import type { DocumentKind, ProjectDocument } from '../../types/document.types';
import Loader from '../ui/Loader';
import ConfirmDialog from '../ui/ConfirmDialog';

const ICONES: Record<DocumentKind, typeof FileText> = {
  text: FileText,
  code: Code2,
  image: ImageIcon,
};

const formatTaille = (o: number) =>
  o < 1024 ? `${o} o` : o < 1024 * 1024 ? `${Math.round(o / 1024)} Ko` : `${(o / 1024 / 1024).toFixed(1)} Mo`;

/** Vignette d'une image : les octets passent par l'API authentifiée, pas par <img src> direct */
const Vignette = ({ projectId, documentId }: { projectId: number; documentId: number }) => {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    let objectUrl: string | null = null;
    let annule = false;
    documentsApi
      .fetchImage(projectId, documentId)
      .then((u) => {
        objectUrl = u;
        if (!annule) setUrl(u);
        else URL.revokeObjectURL(u);
      })
      .catch(() => {});
    return () => {
      annule = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [projectId, documentId]);

  return (
    <div className="w-14 h-14 shrink-0 border border-ink-line bg-paper-warm overflow-hidden flex items-center justify-center">
      {url ? (
        <img src={url} alt="" className="w-full h-full object-cover" />
      ) : (
        <ImageIcon className="w-5 h-5 text-ink-faint" />
      )}
    </div>
  );
};

interface Props {
  projectId: number;
}

export const ProjectDocuments = ({ projectId }: Props) => {
  const [documents, setDocuments] = useState<ProjectDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [aSupprimer, setASupprimer] = useState<ProjectDocument | null>(null);
  const [saisieOuverte, setSaisieOuverte] = useState(false);
  const [nom, setNom] = useState('');
  const [note, setNote] = useState('');
  const [contenu, setContenu] = useState('');
  const [envoi, setEnvoi] = useState(false);
  const inputFichier = useRef<HTMLInputElement>(null);

  useEffect(() => {
    documentsApi
      .list(projectId)
      .then(setDocuments)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [projectId]);

  const televerser = useCallback(
    async (fichiers: FileList | null) => {
      if (!fichiers?.length) return;
      setEnvoi(true);
      for (const fichier of Array.from(fichiers)) {
        try {
          const doc = await documentsApi.upload(projectId, fichier);
          setDocuments((prev) => [doc, ...prev]);
          toast.success(`« ${doc.name} » ajouté`);
        } catch {
          // Motif déjà affiché par l'intercepteur API (format, taille…)
        }
      }
      setEnvoi(false);
      if (inputFichier.current) inputFichier.current.value = '';
    },
    [projectId],
  );

  const ajouterTexte = async () => {
    if (!nom.trim() || !contenu.trim()) return;
    setEnvoi(true);
    try {
      const doc = await documentsApi.addText(projectId, {
        name: nom.trim(),
        content: contenu,
        note: note.trim() || undefined,
        kind: /\.(js|ts|tsx|jsx|py|css|html|sql|sh|go|rs)$/i.test(nom.trim()) ? 'code' : 'text',
      });
      setDocuments((prev) => [doc, ...prev]);
      setNom('');
      setNote('');
      setContenu('');
      setSaisieOuverte(false);
      toast.success(`« ${doc.name} » ajouté`);
    } catch {
      /* déjà toasté */
    } finally {
      setEnvoi(false);
    }
  };

  const basculer = async (doc: ProjectDocument) => {
    setBusyId(doc.id);
    try {
      const maj = await documentsApi.update(projectId, doc.id, { enabled: !doc.enabled });
      setDocuments((prev) => prev.map((d) => (d.id === doc.id ? maj : d)));
    } catch {
      /* déjà toasté */
    } finally {
      setBusyId(null);
    }
  };

  const supprimer = async () => {
    if (!aSupprimer) return;
    try {
      await documentsApi.remove(projectId, aSupprimer.id);
      setDocuments((prev) => prev.filter((d) => d.id !== aSupprimer.id));
      toast.success('Document retiré');
    } catch {
      /* déjà toasté */
    } finally {
      setASupprimer(null);
    }
  };

  const actifs = documents.filter((d) => d.enabled).length;

  return (
    <div className="bg-paper-card shadow-card border border-ink-line p-6 mb-6">
      <div className="flex items-start justify-between gap-4 mb-1">
        <div className="flex items-start gap-3">
          <Paperclip className="w-5 h-5 text-accent mt-1 shrink-0" />
          <div>
            <h2 className="font-display text-xl text-ink">Documents du projet</h2>
            <p className="text-sm text-ink-soft mt-1">
              Dépose ici ce que l'IA ne peut pas deviner : charte, cahier des charges, code
              existant, images de référence. Les documents actifs sont donnés au modèle lors
              des générations, en priorité sur ses suppositions.
            </p>
          </div>
        </div>
        {documents.length > 0 && (
          <span className="shrink-0 text-xs text-ink-faint figures whitespace-nowrap">
            {actifs}/{documents.length} actifs
          </span>
        )}
      </div>

      {/* Dépôt */}
      <div className="mt-5 pt-5 border-t border-ink-line flex flex-wrap gap-2">
        <input
          ref={inputFichier}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => televerser(e.target.files)}
          accept=".txt,.md,.markdown,.csv,.json,.yaml,.yml,.toml,.py,.js,.ts,.tsx,.jsx,.html,.css,.scss,.sh,.sql,.go,.rs,.png,.jpg,.jpeg,.webp,.gif"
        />
        <button
          onClick={() => inputFichier.current?.click()}
          disabled={envoi}
          className="inline-flex items-center gap-2 px-4 py-2 border border-ink-line text-ink hover:border-accent hover:text-accent disabled:opacity-40 transition-colors text-sm font-medium"
        >
          <Upload className="w-4 h-4" />
          {envoi ? 'Envoi…' : 'Téléverser un fichier'}
        </button>
        <button
          onClick={() => setSaisieOuverte((v) => !v)}
          className="inline-flex items-center gap-2 px-4 py-2 border border-ink-line text-ink hover:border-accent hover:text-accent transition-colors text-sm font-medium"
        >
          <Plus className="w-4 h-4" />
          Coller une note
        </button>
        <span className="self-center text-xs text-ink-faint">
          Texte, code et images · pas de PDF (trop coûteux en local)
        </span>
      </div>

      {saisieOuverte && (
        <div className="mt-4 p-4 border border-ink-line bg-paper space-y-3">
          <div className="flex flex-col sm:flex-row gap-2">
            <input
              value={nom}
              onChange={(e) => setNom(e.target.value)}
              placeholder="Nom (ex. charte-graphique.md)"
              className="flex-1 px-3 py-2 bg-paper-card border border-ink-line text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent text-sm"
            />
            <input
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="À quoi ça sert ? (facultatif)"
              className="flex-1 px-3 py-2 bg-paper-card border border-ink-line text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent text-sm"
            />
          </div>
          <textarea
            value={contenu}
            onChange={(e) => setContenu(e.target.value)}
            rows={8}
            placeholder="Colle ici ton texte ou ton code…"
            className="w-full px-3 py-2 bg-paper-card border border-ink-line text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent font-mono text-sm"
          />
          <div className="flex gap-2">
            <button
              onClick={ajouterTexte}
              disabled={!nom.trim() || !contenu.trim() || envoi}
              className="px-4 py-2 bg-accent text-paper hover:opacity-90 disabled:opacity-40 transition-opacity text-sm font-medium"
            >
              {envoi ? 'Ajout…' : 'Ajouter'}
            </button>
            <button
              onClick={() => setSaisieOuverte(false)}
              className="px-4 py-2 border border-ink-line text-ink-soft hover:text-ink transition-colors text-sm"
            >
              Annuler
            </button>
          </div>
        </div>
      )}

      {/* Liste */}
      <div className="mt-5 pt-5 border-t border-ink-line">
        {loading ? (
          <div className="flex justify-center py-6">
            <Loader size="lg" />
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-8">
            <Paperclip className="w-10 h-10 mx-auto mb-3 text-ink-faint" />
            <p className="text-ink-soft">Aucun document pour l'instant</p>
            <p className="text-sm text-ink-faint mt-1">
              Sans documents, l'IA ne dispose que de la description du projet et de ses tâches.
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-ink-line">
            {documents.map((doc) => {
              const Icone = ICONES[doc.kind];
              return (
                <li key={doc.id} className={`py-3 ${doc.enabled ? '' : 'opacity-50'}`}>
                  <div className="flex items-start gap-3">
                    {doc.kind === 'image' ? (
                      <Vignette projectId={projectId} documentId={doc.id} />
                    ) : (
                      <Icone className="w-4 h-4 text-ink-soft mt-1 shrink-0" />
                    )}

                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-ink truncate">{doc.name}</p>
                      {doc.note && <p className="text-sm text-ink-soft">{doc.note}</p>}
                      {doc.excerpt && (
                        <p className="text-xs text-ink-faint font-mono mt-1 line-clamp-2">{doc.excerpt}</p>
                      )}
                      <p className="text-xs text-ink-faint mt-1 figures">
                        {doc.kind === 'image' ? 'Image' : doc.kind === 'code' ? 'Code' : 'Texte'} ·{' '}
                        {formatTaille(doc.size_bytes)}
                      </p>
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        onClick={() => basculer(doc)}
                        disabled={busyId === doc.id}
                        title={doc.enabled ? 'Ne plus transmettre à l\'IA' : 'Transmettre à l\'IA'}
                        className="px-2 py-1 text-xs border border-ink-line text-ink-soft hover:border-accent hover:text-accent disabled:opacity-40 transition-colors"
                      >
                        {doc.enabled ? 'Actif' : 'Inactif'}
                      </button>
                      <button
                        onClick={() => setASupprimer(doc)}
                        title="Retirer du projet"
                        className="p-2 text-ink-soft hover:text-danger transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <ConfirmDialog
        open={!!aSupprimer}
        title="Retirer ce document ?"
        message={`« ${aSupprimer?.name ?? ''} » ne sera plus transmis à l'IA.`}
        confirmLabel="Retirer"
        onCancel={() => setASupprimer(null)}
        onConfirm={supprimer}
      />
    </div>
  );
};

export default ProjectDocuments;

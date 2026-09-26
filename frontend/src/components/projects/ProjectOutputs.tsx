/**
 * Ce que le projet a produit, rassemblé au même endroit.
 *
 * Le résultat d'un projet restait éparpillé dans ses tâches : il fallait copier
 * chaque fichier à la main pour voir le site exister. Ici : la liste des fichiers,
 * un aperçu du site en direct, l'archive .zip, et les liens cassés entre fichiers.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Download, Eye, EyeOff, FileCode2, FileText, Package, RefreshCw, Rss } from 'lucide-react';
import api from '../../services/api';

interface CodeFile {
  path: string;
  task_id: number;
  task_title: string;
  size: number;
  content: string;
}

interface DocumentFile {
  path: string;
  task_id: number;
  task_title: string;
  kind: 'document' | 'veille';
  size: number;
}

interface ProjectFilesResponse {
  entry: string | null;
  code: CodeFile[];
  documents: DocumentFile[];
  coherence: string[];
}

const formatTaille = (o: number) => (o < 1024 ? `${o} o` : `${Math.round(o / 1024)} Ko`);

/** Les alertes du serveur marquent les noms entre `backticks` */
const Alerte = ({ texte }: { texte: string }) => (
  <>
    {texte.split(/`([^`]+)`/).map((morceau, i) =>
      i % 2 ? (
        <code key={i} className="font-mono text-xs bg-paper-warm px-1">{morceau}</code>
      ) : (
        morceau
      ),
    )}
  </>
);

const echapperRegex = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/**
 * Assemble la page d'entrée avec ses feuilles de styles et scripts en ligne : un
 * cadre isolé (srcdoc) ne peut pas aller chercher styles.css ou app.js ailleurs.
 */
export const assemblerApercu = (entry: string, files: CodeFile[]): string => {
  const parChemin = new Map(files.map((f) => [f.path.replace(/^\.\//, ''), f.content]));
  let html = parChemin.get(entry) ?? '';
  const scriptsDiffere: string[] = [];

  for (const [chemin, contenu] of parChemin) {
    const ref = `(?:\\./)?${echapperRegex(chemin)}`;
    if (chemin.endsWith('.css')) {
      html = html.replace(
        new RegExp(`<link\\b[^>]*href=["']${ref}["'][^>]*>`, 'gi'),
        () => `<style>/* ${chemin} */\n${contenu}</style>`,
      );
    } else if (/\.(m?js)$/.test(chemin)) {
      const sur = contenu.replace(/<\/script/gi, '<\\/script');
      html = html.replace(
        new RegExp(`<script\\b([^>]*)src=["']${ref}["']([^>]*)>\\s*</script>`, 'gi'),
        (_m, avant: string, apres: string) => {
          // Un script différé attend le DOM : en ligne, il doit passer en fin de page
          if (/\b(defer|type=["']module["'])/i.test(avant + apres)) {
            scriptsDiffere.push(`<script>/* ${chemin} */\n${sur}</script>`);
            return '';
          }
          return `<script>/* ${chemin} */\n${sur}</script>`;
        },
      );
    }
  }
  if (scriptsDiffere.length) {
    html = /<\/body>/i.test(html)
      ? html.replace(/<\/body>/i, `${scriptsDiffere.join('\n')}\n</body>`)
      : `${html}\n${scriptsDiffere.join('\n')}`;
  }
  return html;
};

interface Props {
  projectId: number;
}

export const ProjectOutputs = ({ projectId }: Props) => {
  const [data, setData] = useState<ProjectFilesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [apercu, setApercu] = useState(false);
  const [ouvert, setOuvert] = useState<string | null>(null);
  const [telechargement, setTelechargement] = useState(false);

  const charger = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get<ProjectFilesResponse>(`/projects/${projectId}/files`);
      setData(response.data);
    } catch {
      // l'intercepteur de l'API affiche déjà l'erreur
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    charger();
  }, [charger]);

  const srcDoc = useMemo(
    () => (data?.entry && apercu ? assemblerApercu(data.entry, data.code) : ''),
    [data, apercu],
  );

  const telecharger = async () => {
    setTelechargement(true);
    try {
      const response = await api.get<Blob>(`/projects/${projectId}/export`, { responseType: 'blob' });
      const nom = /filename="([^"]+)"/.exec(response.headers['content-disposition'] ?? '')?.[1]
        ?? `projet-${projectId}.zip`;
      const url = URL.createObjectURL(response.data);
      const lien = document.createElement('a');
      lien.href = url;
      lien.download = nom;
      lien.click();
      URL.revokeObjectURL(url);
    } catch {
      // l'intercepteur de l'API affiche déjà l'erreur
    } finally {
      setTelechargement(false);
    }
  };

  if (loading && !data) return null;
  if (!data || (data.code.length === 0 && data.documents.length === 0)) return null;

  const fichierOuvert = data.code.find((f) => f.path === ouvert);

  return (
    <div className="bg-paper-card shadow-card border border-ink-line p-6 mb-6">
      <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
        <div className="flex items-start gap-3 min-w-0">
          <Package className="w-5 h-5 text-accent mt-1 shrink-0" />
          <div className="min-w-0">
            <h2 className="font-display text-xl text-ink">Ce que le projet a produit</h2>
            <p className="text-sm text-ink-soft mt-1">
              Les fichiers de code assemblés selon le plan, les documents et les veilles —
              à voir ici, ou à télécharger d'un bloc.
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={charger}
            disabled={loading}
            title="Actualiser"
            className="inline-flex items-center gap-2 px-3 py-2 border border-ink-line text-ink hover:border-accent hover:text-accent disabled:opacity-40 transition-colors text-sm"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          {data.entry && (
            <button
              onClick={() => setApercu((v) => !v)}
              className="inline-flex items-center gap-2 px-4 py-2 border border-ink-line text-ink hover:border-accent hover:text-accent transition-colors text-sm font-medium"
            >
              {apercu ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              {apercu ? "Fermer l'aperçu" : 'Aperçu du site'}
            </button>
          )}
          <button
            onClick={telecharger}
            disabled={telechargement}
            className="inline-flex items-center gap-2 px-4 py-2 bg-accent text-white hover:opacity-90 disabled:opacity-40 transition-opacity text-sm font-medium"
          >
            <Download className="w-4 h-4" />
            {telechargement ? 'Préparation…' : 'Tout télécharger (.zip)'}
          </button>
        </div>
      </div>

      {data.coherence.length > 0 && (
        <div className="border border-warning bg-warning/10 p-4 mb-4">
          <p className="flex items-center gap-2 text-sm font-medium text-ink mb-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-warning" />
            Liens à vérifier entre les fichiers
          </p>
          <ul className="space-y-1 text-sm text-ink-soft list-disc pl-5">
            {data.coherence.map((alerte) => (
              <li key={alerte} className="break-words"><Alerte texte={alerte} /></li>
            ))}
          </ul>
        </div>
      )}

      {apercu && data.entry && (
        <div className="border border-ink-line mb-4">
          <div className="px-3 py-1.5 border-b border-ink-line bg-paper-warm text-xs text-ink-faint">
            {data.entry} — aperçu isolé : le site n'a accès ni à l'orchestrateur ni à tes données
          </div>
          {/* allow-scripts sans allow-same-origin : le code généré reste dans sa boîte */}
          <iframe
            title="Aperçu du site"
            sandbox="allow-scripts allow-forms allow-modals"
            srcDoc={srcDoc}
            className="w-full h-[70vh] bg-white"
          />
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        {data.code.length > 0 && (
          <div className="min-w-0">
            <h3 className="text-xs uppercase tracking-wider text-ink-faint mb-2">Code</h3>
            <ul className="divide-y divide-ink-line border-y border-ink-line">
              {data.code.map((f) => (
                <li key={f.path}>
                  <button
                    onClick={() => setOuvert((p) => (p === f.path ? null : f.path))}
                    className="w-full flex items-center gap-3 py-2 text-left hover:text-accent"
                  >
                    <FileCode2 className="w-4 h-4 shrink-0 text-ink-faint" />
                    <span className="font-mono text-sm shrink-0 max-w-[60%] truncate">{f.path}</span>
                    <span className="text-xs text-ink-faint truncate min-w-0 hidden sm:inline">{f.task_title}</span>
                    <span className="ml-auto text-xs text-ink-faint shrink-0">{formatTaille(f.size)}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
        {data.documents.length > 0 && (
          <div className="min-w-0">
            <h3 className="text-xs uppercase tracking-wider text-ink-faint mb-2">Documents et veilles</h3>
            <ul className="divide-y divide-ink-line border-y border-ink-line">
              {data.documents.map((f) => {
                const Icone = f.kind === 'veille' ? Rss : FileText;
                return (
                  <li key={f.path} className="flex items-center gap-3 py-2 min-w-0">
                    <Icone className="w-4 h-4 shrink-0 text-ink-faint" />
                    <span className="text-sm truncate">{f.task_title}</span>
                    <span className="ml-auto text-xs text-ink-faint shrink-0">{formatTaille(f.size)}</span>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </div>

      {fichierOuvert && (
        <pre className="mt-4 max-h-96 overflow-auto border border-ink-line bg-paper-warm p-4 text-xs font-mono whitespace-pre">
          {fichierOuvert.content}
        </pre>
      )}
    </div>
  );
};

export default ProjectOutputs;
